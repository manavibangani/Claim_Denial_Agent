import requests

claim_reason = "Missing identity proof"

prompt = f"""
A health insurance claim was denied.

Reason:
{claim_reason}

Suggest the next best action.
"""

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
)

result = response.json()

print("\nAI Response:\n")
print(result["response"])