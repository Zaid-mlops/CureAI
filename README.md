# Medical Gemma 3:1B (Local Agent)

## Prerequisites
- Python 3.9+
- Ollama installed
- Gemma 3:1B downloaded:
  ollama pull gemma:3-1b

## Steps

1. Start Ollama
   ollama serve

2. Install dependencies
   pip install -r requirements.txt

3. Run the backend
   uvicorn app:app --reload

4. Backend URL
   http://localhost:8000

## Test API

POST http://localhost:8000/chat

Body:
{
  "message": "Explain hypertension"
}
