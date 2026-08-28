from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from claim_agent import analyze_claim_record, supported_categories
from claim_store import ClaimLoadError, load_claims

app = FastAPI(title="AI Claim Denial Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE = Path(__file__).resolve().parent / "agent_logs.txt"


def log_action(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with LOG_FILE.open("a") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


@app.get("/")
def home():
    return {
        "message": "AI Claim Denial Agent Running",
        "capabilities_endpoint": "/capabilities",
        "claim_analysis_endpoint": "/analyze-claim/{claim_id}",
    }


@app.get("/claims")
def list_claims():
    try:
        claims = load_claims()
    except ClaimLoadError as exc:
        return {"error": str(exc)}

    return {
        "count": len(claims),
        "claims": list(claims.values()),
    }


@app.get("/capabilities")
def capabilities():
    return {
        "supported_categories": supported_categories(),
        "escalation_rules": [
            "Fraud, suspicious, forged, or tampered claims go to human fraud review.",
            "Claims at or above the configured high-value threshold go to senior claims review.",
            "Medical necessity cases go to clinical review.",
            "Unmapped or low-confidence denial reasons go to operations review.",
        ],
    }


@app.get("/analyze-claim/{claim_id}")
def analyze_claim(claim_id: str):
    if not claim_id or not claim_id.strip():
        return {"error": "Claim ID must not be empty."}

    try:
        claims = load_claims()
    except ClaimLoadError as exc:
        return {"error": str(exc)}

    normalized_claim_id = claim_id.strip().upper()
    claim = claims.get(normalized_claim_id)

    if not claim:
        return {"error": "Claim ID not found"}

    decision = analyze_claim_record(claim, all_claims=claims)
    action_result = decision["agent_action_result"]

    log_action(
        " | ".join(
            [
                f"Claim {normalized_claim_id} processed",
                f"Category: {decision['decision_category']}",
                f"CARC: {decision['carc_code']}",
                f"Tool: {decision['tool_used']}",
                f"Human review: {decision['human_intervention_required']}",
            ]
        )
    )

    return {
        "claim_id": claim["claim_id"],
        "patient_name": claim["patient_name"],
        "claim_amount": claim["claim_amount"],
        "policy_type": claim["policy_type"],
        "denial_reason": claim["reason"],
        "decision_category": decision["decision_category"],
        "carc_code": decision["carc_code"],
        "carc_description": decision["carc_description"],
        "priority_level": decision["priority_level"],
        "tool_used": decision["tool_used"],
        "llm_reasoning": decision["llm_reasoning"],
        "risk_flags": decision["risk_flags"],
        "ai_analysis": decision["ai_analysis"],
        "human_intervention_required": decision["human_intervention_required"],
        "complexity_reasons": decision["complexity_reasons"],
        "agent_action_status": action_result["status"],
        "agent_action_result": action_result["message"],
        "escalation_queue": action_result["queue"],
        "appeal_letter": decision["appeal_letter"],
        "processed_at": decision["processed_at"],
    }
