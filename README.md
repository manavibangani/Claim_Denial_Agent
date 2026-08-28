# Claim Denial AI Agent

This project takes a denied health insurance claim and figures out what to do next — automatically.

Instead of a person reading every denial reason and deciding what happens next, this project uses a local AI model to read the reason, understand what it actually means, and pick the right next step: ask for a missing document, send it to a fraud team, check for a duplicate claim, or write an appeal letter.

## Why this project exists

When an insurance claim gets denied, someone has to read the reason and decide what to do about it. That's slow and repetitive. This project automates that first decision using AI, while still sending the tricky or high-risk cases to a real person.

## How it actually works

1. You give the app a claim ID.
2. The app sends the claim's denial reason (plain text) to a local AI model (Llama 3, running through Ollama on your own computer — no paid API, no internet needed for the AI part).
3. The AI model reads the text and decides, on its own, which category the denial falls into. This is real understanding, not simple word-matching — the code never just checks if a specific word like "fraud" appears in the text.
4. That category is matched to a real insurance code (a CARC code — the actual code type used on real insurance paperwork) and to one of four actions the app can take.
5. The app runs that action — for example, it writes a real appeal letter using AI and saves it, or creates a fraud escalation ticket.

## The four actions the agent can take

- **Ask for a missing document** — when the claim is missing an ID document or medical paperwork.
- **Send to fraud review** — when the reason points to fraud, forgery, or suspicious activity.
- **Check for a duplicate claim** — actually looks through the other claims in the system to see if this one was already submitted before.
- **Write an appeal letter** — for anything that could reasonably be appealed (wrong billing code, missing prior authorization, policy disputes, and more). The AI writes a real 2-3 paragraph letter and saves it as a file.

## What makes this a real AI agent, not just a script

A lot of projects like this fake the "AI" part with simple rules like "if the text contains the word X, do Y." This project doesn't do that. The AI model itself reads and understands the denial reason and decides the category — that decision is what drives everything else. You can test this by giving it a denial reason worded completely differently from the examples it was shown, and it still classifies it correctly, because it's reasoning about the meaning, not matching exact words.

## Project structure

```
app.py            - the web server (FastAPI) that exposes the agent over HTTP
claim_agent.py     - the actual AI agent: classifies denials and runs the four actions
carc_codes.py      - the real insurance denial codes used in this project
claim_store.py     - loads and validates claim data from the CSV file
main.py            - a simple command-line version, for testing without the web server
claims.csv         - sample claim data
frontend/          - the web page you use to look up a claim and see the result
tests/             - automated tests for the agent's logic
```

## Running it yourself

You'll need:

- Python 3.10 or newer
- [Ollama](https://ollama.com) installed and running on your machine
- The Llama 3 model pulled once: `ollama pull llama3`

Steps:

```bash
git clone https://github.com/manavibangani/Claim_Denial_Agent.git
cd Claim_Denial_Agent
pip install -r requirements.txt
uvicorn app:app --reload
```

Then open `frontend/index.html` in your browser, type in a claim ID from `claims.csv` (like `CLM101`), and click "Analyze Claim."

To try it from the command line instead of the browser:

```bash
python main.py
```

## Running the tests

```bash
pytest
```

The tests check that the agent picks the right action for different kinds of denial reasons, including reasons worded differently from the training examples, to prove it's really understanding the text and not just matching keywords.

## Being honest about the limits

- This uses a small set of 13 real insurance codes, not the full official list of around 200 — enough to cover realistic cases without turning this into a huge reference table.
- There isn't an official insurance code specifically for "fraud" in real life either — real insurers route fraud cases to a separate investigation team instead of putting a fraud code on paperwork. This project does the same thing and uses a generic code with a note explaining why.
- The AI model runs locally through Ollama, so there's no live hosted demo link — you need Ollama running on your own machine to try it.

## Tech used

- Python, FastAPI (the web server)
- LangChain + Ollama (running Llama 3 locally) for the actual AI reasoning
- Plain HTML/CSS/JS for the front-end page
- Pytest for automated tests
