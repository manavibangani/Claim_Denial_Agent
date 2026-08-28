"""Tests for claim_store.py - CSV loading, malformed rows, and missing claim IDs.

These are pure Python (no LLM calls) so they always run, even without Ollama.
"""

from claim_store import get_claim, load_claims


def test_missing_claim_id_returns_none(tmp_path):
    csv_path = tmp_path / "claims.csv"
    csv_path.write_text(
        "claim_id,patient_name,claim_amount,policy_type,reason\n"
        "CLM001,Jane Doe,1000,Health Plus,Policy expired\n"
    )
    assert get_claim("CLM999", claims_file=csv_path) is None
    assert get_claim("", claims_file=csv_path) is None


def test_malformed_row_is_skipped_not_crashed(tmp_path):
    csv_path = tmp_path / "claims.csv"
    csv_path.write_text(
        "claim_id,patient_name,claim_amount,policy_type,reason\n"
        "CLM001,Jane Doe,1000,Health Plus,Policy expired\n"
        ",Missing Claim Id,2000,Health Plus,Fraud suspicion\n"  # blank claim_id - skipped
        "CLM003,No Reason Given,3000,Health Plus,\n"  # blank reason - skipped
        "CLM004,,,,Data mismatch\n"  # blank patient/amount/policy - kept with safe defaults
    )
    claims = load_claims(csv_path)

    assert "CLM001" in claims
    assert len(claims) == 2  # CLM001 and CLM004 only
    assert "CLM004" in claims
    assert claims["CLM004"]["patient_name"] == "Unknown Patient"
    assert claims["CLM004"]["claim_amount"] == "0"
