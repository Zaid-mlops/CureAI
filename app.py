from flask import Flask, request, jsonify, send_from_directory
import requests
import json
import os
import re
import logging
from asgiref.wsgi import WsgiToAsgi


app = Flask(__name__)

# Allow configuring the Ollama URL via environment variable
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434/api/generate')

# Load system prompt with a safe default if prompt.json is missing or invalid
SYSTEM_PROMPT = (
    "You are a helpful medical assistant. Provide accurate, evidence-based information about health"
    " and medical topics. Always advise users to consult with qualified healthcare professionals for"
    " personalized medical advice, diagnosis, or treatment. Do not provide diagnoses or prescribe"
    " medications. If a user describes symptoms, suggest they seek professional medical help. Answer"
    " questions clearly and empathetically."
)

try:
    with open('prompt.json', 'r', encoding='utf-8') as f:
        prompt_data = json.load(f)
        if isinstance(prompt_data, dict) and 'system_prompt' in prompt_data:
            SYSTEM_PROMPT = prompt_data['system_prompt']
except FileNotFoundError:
    logging.warning('prompt.json not found; using built-in system prompt')
except (json.JSONDecodeError, Exception) as e:
    logging.warning('Could not load prompt.json: %s; using built-in prompt', e)

# If set (default true), the API will only answer medical science questions.
MEDICAL_ONLY = os.environ.get('MEDICAL_ONLY', '1') in ('1', 'true', 'True')

# Lightweight heuristic keyword list to detect medical queries. This is
# intentionally conservative: presence of any keyword will allow the query.
_MEDICAL_KEYWORDS = {
    'symptom', 'symptoms', 'diagnosis', 'diagnose', 'treatment', 'treatments',
    'vaccine', 'vaccination', 'immunization', 'dose', 'dosage', 'side effect',
    'side effects', 'prescribe', 'prescription', 'medication', 'drug', 'antibiotic',
    'antiviral', 'infection', 'infectious', 'bacteria', 'virus', 'viral', 'fungal',
    'pain', 'fever', 'cough', 'headache', 'migraine', 'nausea', 'vomit', 'diarrhea',
    'anxiety', 'depression', 'mental health', 'blood pressure', 'hypertension',
    'cholesterol', 'diabetes', 'insulin', 'cancer', 'tumor', 'oncology', 'cardiac',
    'cardiovascular', 'heart', 'lung', 'pulmonary', 'kidney', 'renal', 'liver',
    'neurology', 'neurological', 'stroke', 'surgery', 'surgical', 'operation',
    'biopsy', 'lab test', 'blood test', 'x-ray', 'mri', 'ct scan', 'ultrasound',
    'imaging', 'pregnancy', 'obstetrics', 'gynecology', 'dermatology', 'allergy',
    'immunology', 'respiratory', 'asthma', 'bronchitis', 'covid', 'covid-19',
    'hiv', 'aids', 'hepatitis', 'vitals', 'dose', 'vaccination'
}

def is_medical_query(text: str) -> bool:
    if not text:
        return False
    s = text.lower()
    # simple substring matching for keywords
    for kw in _MEDICAL_KEYWORDS:
        if kw in s:
            return True
    # allow common medical question forms with medical words
    return False

# Optional model-based classifier: when enabled, the server asks the model to
# classify whether the prompt is a medical science question (YES/NO). This
# provides a stronger signal than simple keyword matching but costs an extra
# model call. If classification fails, we fall back to the keyword heuristic.
MEDICAL_CLASSIFY = os.environ.get('MEDICAL_CLASSIFY', '1') in ('1', 'true', 'True')
CLASSIFIER_MODEL = os.environ.get('CLASSIFIER_MODEL', 'gemma:3.1b')

def classify_with_model(text: str, classifier_model: str) -> bool | None:
    """Return True if model says YES (medical), False if NO, or None if unknown/error."""
    if not text:
        return None

    classifier_prompt = (
        "Classify whether the following user prompt is a medical science question. "
        "Respond with a single word, either YES or NO, and nothing else.\n\n"
        f"Prompt: \"{text}\"\n\nAnswer:"
    )

    payload = {"model": classifier_model, "prompt": classifier_prompt, "stream": False}
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=10)
        resp.raise_for_status()
        try:
            data = resp.json()
            resp_text = data.get('response') if isinstance(data, dict) else resp.text
        except ValueError:
            resp_text = resp.text

        if not resp_text:
            return None

        # Look for explicit yes/no
        if re.search(r"\byes\b", resp_text, re.I):
            return True
        if re.search(r"\bno\b", resp_text, re.I):
            return False

        # Ambiguous – fall back to keyword heuristic
        return is_medical_query(text)
    except requests.RequestException:
        return None


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True, silent=True)
    if not data or 'prompt' not in data:
        return jsonify({'error': 'Prompt is required'}), 400

    user_prompt = data['prompt']
    # enforce medical-only mode
    if MEDICAL_ONLY:
        # If model-based classification is enabled, prefer it.
        if MEDICAL_CLASSIFY:
            cls = classify_with_model(user_prompt, os.environ.get('CLASSIFIER_MODEL', CLASSIFIER_MODEL))
            if cls is False:
                return jsonify({'error': 'Assistant only answers medical science questions. Please ask a medical-related question.'}), 400
            if cls is None:
                # classifier failed -> fall back to keyword heuristic
                if not is_medical_query(user_prompt):
                    return jsonify({'error': 'Assistant only answers medical science questions. Please ask a medical-related question.'}), 400
        else:
            if not is_medical_query(user_prompt):
                return jsonify({'error': 'Assistant only answers medical science questions. Please ask a medical-related question.'}), 400
    model = data.get('model', 'gemma:3.1b')  # Default to gemma 3.1b

    # Combine system prompt with user prompt
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_prompt}\n\nAssistant:"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        response.raise_for_status()
        # If the upstream returns JSON, propagate its response field
        try:
            result = response.json()
            return jsonify({'response': result.get('response', '')})
        except ValueError:
            return jsonify({'response': response.text})
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Could not connect to Ollama server at ' + OLLAMA_URL}), 502
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to Ollama timed out'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '1') in ('1', 'true', 'True')
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', 8000))
    app.run(host=host, port=port, debug=debug)

# Expose an ASGI wrapper so Gunicorn can use Uvicorn workers:
asgi_app = WsgiToAsgi(app)


@app.route('/', methods=['GET'])
def index():
    # Serve the single-file frontend from the static directory
    return send_from_directory('static', 'index.html')
