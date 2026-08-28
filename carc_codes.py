"""Reference table of real CARC (Claim Adjustment Reason Code) codes.

This is a deliberately small subset (13 codes) of the official X12 CARC list —
https://x12.org/codes/claim-adjustment-reason-codes — picked to match the denial
categories this project actually handles. It is NOT the full official list.

Each category maps to the CARC code a real EOB (Explanation of Benefits) would
most plausibly carry for that kind of denial. One exception is called out below.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CarcEntry:
    code: str
    description: str


# category key -> CarcEntry
CARC_TABLE = {
    "missing_identity_proof": CarcEntry(
        "CO-226",
        "Information requested from the patient/insured/responsible party was not "
        "provided or was insufficient/incomplete.",
    ),
    "incomplete_documentation": CarcEntry(
        "CO-16",
        "Claim/service lacks information or has submission/billing error(s) needed "
        "for adjudication.",
    ),
    "coverage_ineligible": CarcEntry(
        "CO-27",
        "Expenses incurred after coverage terminated.",
    ),
    "duplicate_submission": CarcEntry(
        "CO-18",
        "Duplicate claim/service.",
    ),
    "prior_authorization_missing": CarcEntry(
        "CO-197",
        "Precertification/authorization/notification absent.",
    ),
    "medical_necessity_review": CarcEntry(
        "CO-50",
        "These are non-covered services because this is not deemed a medical necessity.",
    ),
    "coding_or_billing_error": CarcEntry(
        "CO-45",
        "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee "
        "arrangement.",
    ),
    "coordination_of_benefits": CarcEntry(
        "CO-22",
        "This care may be covered by another payer per coordination of benefits.",
    ),
    "timely_filing_limit": CarcEntry(
        "CO-29",
        "The time limit for filing has expired.",
    ),
    "provider_network_issue": CarcEntry(
        "CO-109",
        "Claim/service not covered by this payer/contractor. You must send the "
        "claim/service to the correct payer/contractor.",
    ),
    "benefit_limit_reached": CarcEntry(
        "CO-119",
        "Benefit maximum for this time period or occurrence has been reached.",
    ),
    "data_mismatch": CarcEntry(
        "CO-140",
        "Patient/Insured health identification number and name do not match.",
    ),
    # NOTE: there is no official CARC dedicated to "fraud" — real payers route fraud
    # referrals to a Special Investigations Unit (SIU) rather than putting a
    # fraud-specific code on a member-facing EOB. CO-A1 (a generic "claim/service
    # denied" header code, normally paired with a more specific remark code) is used
    # here as the closest honest fit, since the real workflow value is the SIU
    # escalation itself, not the code.
    "fraud_risk": CarcEntry(
        "CO-A1",
        "Claim/service denied. (Generic header code — fraud referrals are handled via "
        "Special Investigations Unit review rather than a dedicated consumer-facing CARC.)",
    ),
}

# Reasons the LLM could not confidently classify into any of the categories above.
UNMAPPED_CATEGORY = "unmapped_denial_reason"


def get_carc(category: str):
    """Return the CarcEntry for a category, or None if unmapped/unknown."""
    return CARC_TABLE.get(category)


def category_label(category: str) -> str:
    """Human-readable label, e.g. 'missing_identity_proof' -> 'Missing Identity Proof'."""
    return category.replace("_", " ").title()
