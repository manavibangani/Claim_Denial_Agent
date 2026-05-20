from dataclasses import asdict, dataclass
from datetime import datetime


HIGH_VALUE_THRESHOLD = 20000


@dataclass
class DenialRule:
    category: str
    keywords: tuple[str, ...]
    priority: str
    action: str
    next_step: str
    automation_type: str
    confidence: float
    requires_human: bool = False
    escalation_queue: str | None = None


DENIAL_RULES = (
    DenialRule(
        category="Fraud Risk",
        keywords=("fraud", "misrepresentation", "suspicious", "forged", "tampered"),
        priority="Critical",
        action="Escalate to Fraud Investigation Team",
        next_step="Create a fraud review case and pause automated processing.",
        automation_type="escalation_ticket",
        confidence=0.98,
        requires_human=True,
        escalation_queue="Fraud Investigation Team",
    ),
    DenialRule(
        category="Missing Identity Proof",
        keywords=("identity", "id proof", "kyc", "government id", "address proof"),
        priority="Medium",
        action="Request Identity Proof",
        next_step="Ask the member to upload a valid government identity document.",
        automation_type="member_document_request",
        confidence=0.95,
    ),
    DenialRule(
        category="Incomplete Documentation",
        keywords=("incomplete", "missing document", "medical document", "report missing", "discharge summary"),
        priority="Medium",
        action="Request Missing Medical Documents",
        next_step="Ask the member to upload the missing medical records.",
        automation_type="member_document_request",
        confidence=0.94,
    ),
    DenialRule(
        category="Coverage Ineligible",
        keywords=("policy expired", "not covered", "coverage ended", "lapsed", "inactive policy"),
        priority="Low",
        action="Auto-Reject Claim",
        next_step="Send an automated rejection notice with coverage details and appeal options.",
        automation_type="auto_rejection_notice",
        confidence=0.93,
    ),
    DenialRule(
        category="Duplicate Submission",
        keywords=("duplicate", "already submitted", "repeat claim", "same invoice"),
        priority="Medium",
        action="Run Duplicate Claim Validation",
        next_step="Check prior submissions and notify the member if duplicate is confirmed.",
        automation_type="duplicate_check",
        confidence=0.92,
    ),
    DenialRule(
        category="Prior Authorization Missing",
        keywords=("prior authorization", "pre authorization", "preauth", "pre-auth", "authorization missing"),
        priority="High",
        action="Request Prior Authorization Evidence",
        next_step="Ask the provider or member for authorization details before appeal review.",
        automation_type="provider_information_request",
        confidence=0.91,
    ),
    DenialRule(
        category="Medical Necessity Review",
        keywords=("medical necessity", "not medically necessary", "experimental", "investigational"),
        priority="High",
        action="Prepare Clinical Review Packet",
        next_step="Collect clinical notes and route the case for nurse or medical review.",
        automation_type="clinical_packet_preparation",
        confidence=0.88,
        requires_human=True,
        escalation_queue="Clinical Review Team",
    ),
    DenialRule(
        category="Coding Or Billing Error",
        keywords=("coding", "billing", "cpt", "icd", "modifier", "diagnosis code", "procedure code"),
        priority="Medium",
        action="Request Corrected Claim",
        next_step="Ask the provider to resubmit the claim with corrected coding details.",
        automation_type="provider_correction_request",
        confidence=0.90,
    ),
    DenialRule(
        category="Coordination Of Benefits",
        keywords=("coordination of benefits", "cob", "primary insurer", "secondary insurer", "other insurance"),
        priority="Medium",
        action="Request Primary Insurer Explanation Of Benefits",
        next_step="Ask the member for primary payer details or an explanation of benefits.",
        automation_type="member_information_request",
        confidence=0.89,
    ),
    DenialRule(
        category="Timely Filing Limit",
        keywords=("timely filing", "late submission", "filing limit", "submitted late"),
        priority="Low",
        action="Auto-Reject Or Request Late-Filing Proof",
        next_step="Check filing date rules and request proof only when an exception may apply.",
        automation_type="filing_rule_check",
        confidence=0.88,
    ),
    DenialRule(
        category="Provider Network Issue",
        keywords=("out of network", "provider network", "non network", "unauthorized provider"),
        priority="Medium",
        action="Verify Network Exception Eligibility",
        next_step="Check emergency, referral, and network exception rules before final denial.",
        automation_type="network_rule_check",
        confidence=0.87,
    ),
    DenialRule(
        category="Benefit Limit Reached",
        keywords=("limit exhausted", "benefit limit", "annual limit", "maximum benefit", "cap exceeded"),
        priority="Low",
        action="Validate Benefit Limit",
        next_step="Verify accumulated benefits and send a limit explanation if confirmed.",
        automation_type="benefit_limit_check",
        confidence=0.88,
    ),
    DenialRule(
        category="Data Mismatch",
        keywords=("data mismatch", "name mismatch", "date of birth mismatch", "member mismatch", "invalid member"),
        priority="Medium",
        action="Request Data Correction",
        next_step="Ask for corrected member or claim details and retry automated validation.",
        automation_type="data_correction_request",
        confidence=0.90,
    ),
)


def parse_amount(value):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except ValueError:
        return 0


def match_denial_rule(reason):
    reason_lower = reason.lower()

    for rule in DENIAL_RULES:
        matched_keywords = [
            keyword for keyword in rule.keywords if keyword in reason_lower
        ]

        if matched_keywords:
            return rule, matched_keywords

    return DenialRule(
        category="Unmapped Denial Reason",
        keywords=(),
        priority="High",
        action="Escalate to Manual Review",
        next_step="Route to an operations reviewer because no rule matched the denial reason.",
        automation_type="manual_review_ticket",
        confidence=0.45,
        requires_human=True,
        escalation_queue="Claims Operations Review",
    ), []


def build_automation_result(rule, claim, risk_flags, human_intervention):
    claim_id = claim["claim_id"]
    patient_name = claim["patient_name"]

    if human_intervention:
        queue = rule.escalation_queue or "Senior Claims Review"
        return {
            "status": "queued_for_human_review",
            "message": f"Escalation ticket created in {queue} for claim {claim_id}.",
            "queue": queue,
        }

    if rule.automation_type in {
        "member_document_request",
        "member_information_request",
        "data_correction_request",
    }:
        return {
            "status": "automated_request_sent",
            "message": f"Automated request sent to {patient_name}: {rule.next_step}",
            "queue": None,
        }

    if rule.automation_type.startswith("provider"):
        return {
            "status": "provider_request_sent",
            "message": f"Provider follow-up generated for claim {claim_id}: {rule.next_step}",
            "queue": None,
        }

    if rule.automation_type == "auto_rejection_notice":
        return {
            "status": "auto_rejected",
            "message": f"Claim {claim_id} marked rejected and notice generated.",
            "queue": None,
        }

    return {
        "status": "automated_validation_started",
        "message": f"{rule.action} started for claim {claim_id}.",
        "queue": None,
    }


def analyze_claim_record(claim):
    reason = claim["reason"].strip()
    claim_amount = parse_amount(claim["claim_amount"])
    rule, matched_keywords = match_denial_rule(reason)
    risk_flags = []
    complexity_reasons = []

    if claim_amount >= HIGH_VALUE_THRESHOLD:
        risk_flags.append("high_claim_value")
        complexity_reasons.append(
            f"Claim amount {claim_amount} is at or above {HIGH_VALUE_THRESHOLD}."
        )

    if rule.requires_human:
        risk_flags.append("specialist_review_required")
        complexity_reasons.append(
            f"{rule.category} requires specialist human review."
        )

    if rule.confidence < 0.70:
        risk_flags.append("low_classification_confidence")
        complexity_reasons.append("The denial reason did not match a known automation rule.")

    human_intervention = bool(complexity_reasons)
    priority = "High" if human_intervention and rule.priority != "Critical" else rule.priority
    automation_result = build_automation_result(
        rule=rule,
        claim=claim,
        risk_flags=risk_flags,
        human_intervention=human_intervention,
    )
    analysis = (
        f"Decision Category: {rule.category}\n"
        f"Priority Level: {priority}\n"
        f"Automation Confidence: {round(rule.confidence * 100)}%\n"
        f"Suggested Action: {rule.action}\n"
        f"Next Step: {rule.next_step}"
    )

    return {
        "decision_category": rule.category,
        "priority_level": priority,
        "suggested_action": rule.action,
        "next_step": rule.next_step,
        "automation_type": rule.automation_type,
        "automation_confidence": rule.confidence,
        "human_intervention_required": human_intervention,
        "complexity_reasons": complexity_reasons,
        "risk_flags": risk_flags,
        "matched_keywords": matched_keywords,
        "agent_action_result": automation_result,
        "ai_analysis": analysis,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
    }


def supported_categories():
    return [asdict(rule) for rule in DENIAL_RULES]
