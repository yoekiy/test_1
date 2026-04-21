import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "deepseek-r1:7b"

def call_deepseek(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["response"]
