import requests
import csv

# Load claims data from CSV
claims = {}

with open("claims.csv", mode="r") as file:
    reader = csv.DictReader(file)

    for row in reader:
        claims[row["claim_id"]] = row["reason"]

# Ask user for claim ID
claim_id = input("Enter Claim ID: ")

# Retrieve denial reason
claim_reason = claims.get(claim_id)

# Handle invalid claim ID
if not claim_reason:
    print("Claim ID not found")
    exit()

# Create prompt for AI
prompt = f"""
A health insurance claim was denied.

Denial reason:
{claim_reason}

Return:
1. Decision Category
2. Priority Level
3. Suggested Next Action

Keep response short and structured.
"""

# Send request to Ollama
response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
)

# Convert response
result = response.json()

# Print AI response
print("\nAI Suggestion:\n")
print(result["response"])