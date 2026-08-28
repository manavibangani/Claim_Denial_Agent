from claim_agent import analyze_claim_record
from claim_store import ClaimLoadError, load_claims

try:
    claims = load_claims()
except ClaimLoadError as exc:
    print(f"Could not load claims: {exc}")
    exit(1)

claim_id = input("Enter Claim ID: ").strip().upper()

if not claim_id:
    print("Claim ID must not be empty")
    exit(1)

claim = claims.get(claim_id)

if not claim:
    print("Claim ID not found")
    exit(1)

decision = analyze_claim_record(claim, all_claims=claims)
action_result = decision["agent_action_result"]

print("\nAI Claim Denial Agent Analysis\n")
print(f"Claim ID: {claim['claim_id']}")
print(f"Patient Name: {claim['patient_name']}")
print(f"Claim Amount: {claim['claim_amount']}")
print(f"Policy Type: {claim['policy_type']}")
print(f"Denial Reason: {claim['reason']}")
print(f"Decision Category: {decision['decision_category']}")
print(f"CARC Code: {decision['carc_code']}")
print(f"CARC Description: {decision['carc_description']}")
print(f"Priority Level: {decision['priority_level']}")
print(f"Tool Used: {decision['tool_used']}")
print(f"LLM Reasoning: {decision['llm_reasoning']}")
print(f"Human Intervention Required: {decision['human_intervention_required']}")
print(f"Agent Action Status: {action_result['status']}")
print(f"Agent Action Result: {action_result['message']}")

if decision["risk_flags"]:
    print("Risk Flags:")
    for flag in decision["risk_flags"]:
        print(f"- {flag}")

if decision["complexity_reasons"]:
    print("Complexity Reasons:")
    for reason in decision["complexity_reasons"]:
        print(f"- {reason}")

if decision["appeal_letter"]:
    print("\nAppeal Letter:\n")
    print(decision["appeal_letter"])
