"""LLM-driven claim denial routing agent.

How this actually works (for anyone reading this file, including future me in an
interview): the denial reason text is handed to a local llama3 model (via Ollama +
langchain-ollama). The model reads the free-text reason and decides, on its own,
which of 13 CARC-coded categories it belongs to - there is no `if "fraud" in text`
anywhere in this file. That category decision drives two things:

  1. A CARC (Claim Adjustment Reason Code) label + description, from carc_codes.py.
  2. Which of the four workflow tools gets called (request_missing_document,
     escalate_to_fraud_review, check_duplicate_claim, draft_appeal_letter) - via a
     fixed, auditable category -> tool lookup table (CATEGORY_TO_TOOL below).

Why route tool selection through a category instead of asking the LLM to name a
tool directly: several categories legitimately land on the same tool (nine
different appealable reasons all end up at draft_appeal_letter), and a fixed
lookup table guarantees the tool name is always one Python actually recognizes -
the LLM can't accidentally call a tool that doesn't exist. The classification
step is still 100% the model's own reasoning over the text.

llama3 (via Ollama) does not support native function/tool calling - only newer
models like llama3.1+ do. So instead of `.bind_tools()`, this uses the documented
fallback: ask the model to return structured JSON, and dispatch on that JSON in
Python. See classify_denial_reason() below.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from carc_codes import UNMAPPED_CATEGORY, category_label, get_carc

HIGH_VALUE_THRESHOLD = 20000
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

APPEALS_DIR = Path(__file__).resolve().parent / "appeals"

VALID_CATEGORIES = {
    "missing_identity_proof",
    "incomplete_documentation",
    "fraud_risk",
    "duplicate_submission",
    "coverage_ineligible",
    "prior_authorization_missing",
    "medical_necessity_review",
    "coding_or_billing_error",
    "coordination_of_benefits",
    "timely_filing_limit",
    "provider_network_issue",
    "benefit_limit_reached",
    "data_mismatch",
    UNMAPPED_CATEGORY,
}

# category -> which of the four tools handles it
CATEGORY_TO_TOOL = {
    "missing_identity_proof": "request_missing_document",
    "incomplete_documentation": "request_missing_document",
    "fraud_risk": "escalate_to_fraud_review",
    "duplicate_submission": "check_duplicate_claim",
    "coverage_ineligible": "draft_appeal_letter",
    "prior_authorization_missing": "draft_appeal_letter",
    "medical_necessity_review": "draft_appeal_letter",
    "coding_or_billing_error": "draft_appeal_letter",
    "coordination_of_benefits": "draft_appeal_letter",
    "timely_filing_limit": "draft_appeal_letter",
    "provider_network_issue": "draft_appeal_letter",
    "benefit_limit_reached": "draft_appeal_letter",
    "data_mismatch": "draft_appeal_letter",
    UNMAPPED_CATEGORY: "escalate_to_manual_review",
}

# category -> (priority, requires_human, escalation_queue)
CATEGORY_METADATA = {
    "missing_identity_proof": ("Medium", False, None),
    "incomplete_documentation": ("Medium", False, None),
    "fraud_risk": ("Critical", True, "Fraud Investigation Team"),
    "duplicate_submission": ("Medium", False, None),
    "coverage_ineligible": ("Low", False, None),
    "prior_authorization_missing": ("High", False, None),
    "medical_necessity_review": ("High", True, "Clinical Review Team"),
    "coding_or_billing_error": ("Medium", False, None),
    "coordination_of_benefits": ("Medium", False, None),
    "timely_filing_limit": ("Low", False, None),
    "provider_network_issue": ("Medium", False, None),
    "benefit_limit_reached": ("Low", False, None),
    "data_mismatch": ("Medium", False, None),
    UNMAPPED_CATEGORY: ("High", True, "Claims Operations Review"),
}

CLASSIFIER_SYSTEM_PROMPT = """You are a claims processing agent for a health insurance company. You will be given the denial reason text for a claim. Reason step by step about what actually caused the denial, then classify it into exactly ONE of these categories:

- missing_identity_proof: a missing/unverifiable identity or KYC document (government ID, address proof).
- incomplete_documentation: missing/incomplete medical paperwork (discharge summary, medical report, treatment notes) - NOT identity documents.
- fraud_risk: fraud, intentional misrepresentation, forged/altered/tampered documents, or suspicious activity.
- duplicate_submission: this exact claim/invoice appears to have been submitted or paid more than once.
- coverage_ineligible: the policy is expired, lapsed, inactive, or the service isn't covered by the plan at all.
- prior_authorization_missing: prior authorization / precertification / pre-approval was required but missing.
- medical_necessity_review: the treatment is considered not medically necessary or experimental/investigational.
- coding_or_billing_error: wrong or inconsistent procedure/diagnosis codes, modifiers, or billing errors.
- coordination_of_benefits: another insurer (primary/secondary payer) should be billed first.
- timely_filing_limit: the claim was submitted after the insurer's filing deadline.
- provider_network_issue: the provider or facility is out-of-network or not on the approved list.
- benefit_limit_reached: an annual or lifetime benefit/coverage limit has been used up.
- data_mismatch: patient identity/date-of-birth/name/member-ID data on the claim doesn't match records.
- unmapped_denial_reason: use ONLY if truly none of the above fit.

Examples:
- "Out of network provider" -> provider_network_issue
- "Date of birth mismatch" -> data_mismatch
- "Missing identity proof" -> missing_identity_proof
- "Claim already paid under a previous submission" -> duplicate_submission
- "Forged signature on claim form" -> fraud_risk
- "Incorrect diagnosis code" -> coding_or_billing_error

Respond with ONLY a JSON object, no other text, in this exact key order:
{"reasoning": "<one sentence on what the denial reason actually means>", "category": "<one of the category keys above>"}
"""

LETTER_SYSTEM_PROMPT = """You write formal insurance appeal letters on behalf of a claims department. Write a professional, factual 2-3 paragraph appeal letter that:
- References the specific claim ID, patient name, and claim amount given.
- States the CARC code and its description as the reason the claim was denied.
- Makes a reasonable, professional case for why the claim should be reconsidered.
- Closes with a request for reconsideration and a point of contact.

Do not use placeholders like [Your Name] - sign it "Claims Appeals Desk". Output only the letter body, no subject line, no JSON, no markdown formatting.
"""


_classifier_llm = None
_letter_llm = None


def _get_classifier_llm():
    global _classifier_llm
    if _classifier_llm is None:
        _classifier_llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            format="json",
        )
    return _classifier_llm


def _get_letter_llm():
    global _letter_llm
    if _letter_llm is None:
        _letter_llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
        )
    return _letter_llm


def _extract_json_object(text: str):
    """Best-effort extraction of a JSON object from an LLM response.

    ChatOllama with format="json" almost always returns clean JSON, but this
    guards against the odd case of stray text/markdown fences around it.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def classify_denial_reason(reason: str):
    """Ask the LLM to classify a denial reason. This is the actual decision point.

    Returns (category, reasoning). Falls back to the unmapped category (with an
    explanatory reasoning string) if the LLM call fails or returns something we
    can't parse into a known category - it never falls back to keyword matching.
    """
    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=f'Denial reason: "{reason}"\n\nClassify it.'),
    ]

    try:
        response = _get_classifier_llm().invoke(messages)
    except Exception as exc:  # Ollama unreachable, model missing, etc.
        return UNMAPPED_CATEGORY, f"LLM call failed ({exc}); routed to manual review."

    parsed = _extract_json_object(response.content)

    if not parsed or "category" not in parsed:
        return (
            UNMAPPED_CATEGORY,
            "LLM response could not be parsed into a category; routed to manual review.",
        )

    category = parsed.get("category")
    reasoning = parsed.get("reasoning", "").strip() or "No reasoning provided by the model."

    if category not in VALID_CATEGORIES:
        return (
            UNMAPPED_CATEGORY,
            f"LLM returned an unrecognized category ('{category}'); routed to manual review.",
        )

    return category, reasoning


def parse_amount(value):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Tools. Each one is a concrete workflow action the agent can take. The LLM
# only decides *which* of these to call (via the category it assigns); the
# arguments come from the trusted claim record itself, not from the model, so
# the model can't hallucinate a claim amount or patient name.
# ---------------------------------------------------------------------------

def request_missing_document(claim_id, reason):
    return {
        "status": "automated_request_sent",
        "message": (
            f"Automated document request sent for claim {claim_id}: please upload "
            f"the missing identity/KYC or medical documentation referenced in "
            f"\"{reason}\"."
        ),
        "queue": None,
    }


def escalate_to_fraud_review(claim_id, reason):
    return {
        "status": "queued_for_human_review",
        "message": f"Escalation ticket created in Fraud Investigation Team for claim {claim_id}.",
        "queue": "Fraud Investigation Team",
    }


def check_duplicate_claim(claim_id, reason, claim=None, all_claims=None):
    """Actually scans the other loaded claims for a same patient/amount/policy match
    instead of just returning a canned string - a lightweight but real duplicate check.
    """
    if not claim or not all_claims:
        return {
            "status": "duplicate_check_incomplete",
            "message": f"Could not run duplicate validation for claim {claim_id}: no claim dataset available.",
            "queue": "Claims Operations Review",
        }

    for other_id, other in all_claims.items():
        if other_id == claim_id.upper():
            continue
        same_patient = other.get("patient_name") == claim.get("patient_name")
        same_amount = other.get("claim_amount") == claim.get("claim_amount")
        same_policy = other.get("policy_type") == claim.get("policy_type")
        if same_patient and same_amount and same_policy:
            return {
                "status": "duplicate_confirmed",
                "message": (
                    f"Potential duplicate found: claim {other_id} matches claim {claim_id} "
                    f"on patient, amount, and policy type."
                ),
                "queue": "Claims Operations Review",
            }

    return {
        "status": "no_duplicate_found",
        "message": f"No matching duplicate claims found for {claim_id}; proceeding with standard review.",
        "queue": None,
    }


def draft_appeal_letter(claim_id, reason, patient_name, claim_amount, category=None, carc_code=None, carc_description=None):
    """Generates a real appeal letter via the LLM and persists it to appeals/<claim_id>.json."""
    prompt = (
        f"Claim ID: {claim_id}\n"
        f"Patient name: {patient_name}\n"
        f"Claim amount: {claim_amount}\n"
        f"Denial reason (insurer's stated reason): {reason}\n"
        f"CARC code: {carc_code or 'N/A'}\n"
        f"CARC description: {carc_description or 'N/A'}\n\n"
        "Write the appeal letter now."
    )
    messages = [SystemMessage(content=LETTER_SYSTEM_PROMPT), HumanMessage(content=prompt)]

    try:
        response = _get_letter_llm().invoke(messages)
        letter_text = response.content.strip()
    except Exception as exc:
        letter_text = (
            f"[Letter generation failed: {exc}]\n\n"
            f"Manual appeal drafting required for claim {claim_id} ({patient_name}), "
            f"denied under {carc_code or 'an unmapped reason'}: {reason}."
        )

    record = {
        "claim_id": claim_id,
        "patient_name": patient_name,
        "claim_amount": claim_amount,
        "denial_reason": reason,
        "category": category,
        "carc_code": carc_code,
        "carc_description": carc_description,
        "letter_text": letter_text,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    APPEALS_DIR.mkdir(parents=True, exist_ok=True)
    appeal_path = APPEALS_DIR / f"{claim_id}.json"
    with appeal_path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return {
        "status": "appeal_letter_drafted",
        "message": f"Appeal letter drafted and saved to {appeal_path.name} for claim {claim_id}.",
        "queue": None,
        "appeal_letter": letter_text,
    }


def escalate_to_manual_review(claim_id, reason):
    return {
        "status": "queued_for_human_review",
        "message": f"No confident category match for claim {claim_id}; routed to Claims Operations Review.",
        "queue": "Claims Operations Review",
    }


TOOL_FUNCTIONS = {
    "request_missing_document": request_missing_document,
    "escalate_to_fraud_review": escalate_to_fraud_review,
    "check_duplicate_claim": check_duplicate_claim,
    "draft_appeal_letter": draft_appeal_letter,
    "escalate_to_manual_review": escalate_to_manual_review,
}


def dispatch_tool(tool_name, claim, category, carc_entry, all_claims=None):
    claim_id = claim["claim_id"]
    reason = claim["reason"]
    patient_name = claim["patient_name"]
    claim_amount = claim["claim_amount"]

    if tool_name == "check_duplicate_claim":
        return check_duplicate_claim(claim_id, reason, claim=claim, all_claims=all_claims)

    if tool_name == "draft_appeal_letter":
        return draft_appeal_letter(
            claim_id,
            reason,
            patient_name,
            claim_amount,
            category=category,
            carc_code=carc_entry.code if carc_entry else None,
            carc_description=carc_entry.description if carc_entry else None,
        )

    tool_fn = TOOL_FUNCTIONS[tool_name]
    return tool_fn(claim_id, reason)


def analyze_claim_record(claim, all_claims=None):
    """Runs the full pipeline: LLM classification -> CARC lookup -> tool dispatch."""
    reason = (claim.get("reason") or "").strip()
    claim_amount = parse_amount(claim.get("claim_amount"))

    if not reason:
        category, reasoning = UNMAPPED_CATEGORY, "Claim has no denial reason text to classify."
    else:
        category, reasoning = classify_denial_reason(reason)

    carc_entry = get_carc(category)
    priority, requires_human, escalation_queue = CATEGORY_METADATA[category]
    tool_name = CATEGORY_TO_TOOL[category]

    risk_flags = []
    complexity_reasons = []

    if claim_amount >= HIGH_VALUE_THRESHOLD:
        risk_flags.append("high_claim_value")
        complexity_reasons.append(f"Claim amount {claim_amount} is at or above {HIGH_VALUE_THRESHOLD}.")
        requires_human = True
        if priority not in ("Critical", "High"):
            priority = "High"
        escalation_queue = escalation_queue or "Senior Claims Review"

    if requires_human and category != UNMAPPED_CATEGORY:
        complexity_reasons.append(f"{category_label(category)} requires specialist human review.")

    if category == UNMAPPED_CATEGORY:
        risk_flags.append("low_classification_confidence")
        complexity_reasons.append("The denial reason did not match a known CARC category.")

    action_result = dispatch_tool(tool_name, claim, category, carc_entry, all_claims=all_claims)

    analysis = (
        f"Category: {category_label(category)}\n"
        f"CARC Code: {carc_entry.code if carc_entry else 'N/A'}\n"
        f"Priority: {priority}\n"
        f"Tool Selected: {tool_name}\n"
        f"LLM Reasoning: {reasoning}"
    )

    return {
        "decision_category": category_label(category),
        "carc_code": carc_entry.code if carc_entry else None,
        "carc_description": carc_entry.description if carc_entry else None,
        "priority_level": priority,
        "tool_used": tool_name,
        "llm_reasoning": reasoning,
        "human_intervention_required": requires_human,
        "complexity_reasons": complexity_reasons,
        "risk_flags": risk_flags,
        "agent_action_result": action_result,
        "ai_analysis": analysis,
        "appeal_letter": action_result.get("appeal_letter"),
        "processed_at": datetime.now().isoformat(timespec="seconds"),
    }


def supported_categories():
    """Returns the CARC reference table in a shape the /capabilities endpoint can serve."""
    result = []
    for category in CATEGORY_TO_TOOL:
        entry = get_carc(category)
        if entry is None:
            continue
        priority, requires_human, queue = CATEGORY_METADATA[category]
        result.append(
            {
                "category": category_label(category),
                "carc_code": entry.code,
                "carc_description": entry.description,
                "tool": CATEGORY_TO_TOOL[category],
                "priority": priority,
                "requires_human": requires_human,
                "escalation_queue": queue,
            }
        )
    return result
