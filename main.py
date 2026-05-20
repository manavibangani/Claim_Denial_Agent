import csv

from claim_agent import analyze_claim_record


def load_claims():
    claims = {}

    with open("claims.csv", mode="r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            claims[row["claim_id"].upper()] = row

    return claims


claims = load_claims()
claim_id = input("Enter Claim ID: ").strip().upper()
claim = claims.get(claim_id)

if not claim:
    print("Claim ID not found")
    exit()

decision = analyze_claim_record(claim)
action_result = decision["agent_action_result"]

print("\nAI Claim Denial Agent Analysis\n")
print(f"Claim ID: {claim['claim_id']}")
print(f"Patient Name: {claim['patient_name']}")
print(f"Claim Amount: {claim['claim_amount']}")
print(f"Policy Type: {claim['policy_type']}")
print(f"Denial Reason: {claim['reason']}")
print(f"Decision Category: {decision['decision_category']}")
print(f"Priority Level: {decision['priority_level']}")
print(f"Automation Type: {decision['automation_type']}")
print(f"Automation Confidence: {round(decision['automation_confidence'] * 100)}%")
print(f"Suggested Action: {decision['suggested_action']}")
print(f"Next Step: {decision['next_step']}")
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
