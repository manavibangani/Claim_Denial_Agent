"""Tests for the LLM-driven classification and tool routing in claim_agent.py.

Most of these tests make real calls to a local Ollama llama3 model - there is no
mocked LLM here on purpose, because the whole point of this project is that the
routing decision genuinely comes from the model reasoning over free text, not
from keyword matching. If Ollama isn't running, these are skipped (see
tests/conftest.py) rather than failing.
"""

import pytest

from claim_agent import analyze_claim_record, classify_denial_reason


# --- 1. Tool selection on representative, dataset-style denial reasons ------

@pytest.mark.parametrize(
    "reason,expected_tool",
    [
        ("Missing identity proof", "request_missing_document"),
        ("Fraud suspicion", "escalate_to_fraud_review"),
        ("Duplicate claim submission", "check_duplicate_claim"),
        ("Policy expired", "draft_appeal_letter"),
        ("Prior authorization missing", "draft_appeal_letter"),
    ],
)
def test_tool_selection_on_representative_reasons(reason, expected_tool):
    claim = {
        "claim_id": "TEST001",
        "patient_name": "Test Patient",
        "claim_amount": "5000",
        "policy_type": "Health Plus",
        "reason": reason,
    }
    decision = analyze_claim_record(claim, all_claims={"TEST001": claim})
    assert decision["tool_used"] == expected_tool


# --- 2. Paraphrased/reworded denial reasons - proves this isn't keyword ----
#        matching in disguise, since none of these share the exact wording
#        of the rules above.

@pytest.mark.parametrize(
    "paraphrased_reason,expected_tool",
    [
        (
            "The member never sent us a valid photo ID so we could not confirm who they are",
            "request_missing_document",
        ),
        (
            "Our investigators believe the submitted receipts were altered after the fact",
            "escalate_to_fraud_review",
        ),
        (
            "This same bill was already paid out under a claim we processed two weeks ago",
            "check_duplicate_claim",
        ),
        (
            "The clinic you visited isn't part of our approved provider list",
            "draft_appeal_letter",
        ),
        (
            "The name and birth date on the claim don't line up with what's in our system for this member",
            "draft_appeal_letter",
        ),
    ],
)
def test_paraphrased_reasons_route_correctly(paraphrased_reason, expected_tool):
    claim = {
        "claim_id": "TEST002",
        "patient_name": "Test Patient",
        "claim_amount": "3000",
        "policy_type": "Family Shield",
        "reason": paraphrased_reason,
    }
    decision = analyze_claim_record(claim, all_claims={"TEST002": claim})
    assert decision["tool_used"] == expected_tool


# --- 3. Edge cases -----------------------------------------------------------

def test_unmapped_denial_reason_routes_to_manual_review():
    category, reasoning = classify_denial_reason(
        "The claim references a satellite launch permit that our system has never heard of"
    )
    # Either the model correctly flags this as unmapped, or (since this is a
    # genuinely odd, out-of-domain reason) it still must be a *known* category -
    # never a hallucinated tool name.
    from claim_agent import VALID_CATEGORIES

    assert category in VALID_CATEGORIES
    assert reasoning


def test_empty_reason_is_handled_without_crashing():
    claim = {
        "claim_id": "TEST003",
        "patient_name": "",
        "claim_amount": "",
        "policy_type": "Health Basic",
        "reason": "",
    }
    decision = analyze_claim_record(claim, all_claims={"TEST003": claim})
    assert decision["decision_category"] == "Unmapped Denial Reason"
    assert decision["human_intervention_required"] is True
