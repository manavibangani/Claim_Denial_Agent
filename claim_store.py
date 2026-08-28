"""Shared claim-loading logic used by both the FastAPI app (app.py) and the CLI (main.py).

This module exists so claim CSV parsing, validation, and lookup live in exactly one
place instead of being copy-pasted between the API and the CLI entry point.
"""

import csv
from pathlib import Path

REQUIRED_FIELDS = ("claim_id", "patient_name", "claim_amount", "policy_type", "reason")

CLAIMS_FILE = Path(__file__).resolve().parent / "claims.csv"


class ClaimLoadError(Exception):
    """Raised when the claims CSV is missing or malformed beyond repair."""


def _row_is_usable(row):
    """A row is usable if it has a non-empty claim_id and reason.

    Other blank fields (patient name, amount, policy type) are tolerated and
    normalized to safe defaults so one bad row doesn't take down the whole file.
    """
    claim_id = (row.get("claim_id") or "").strip()
    reason = (row.get("reason") or "").strip()
    return bool(claim_id) and bool(reason)


def _normalize_row(row):
    return {
        "claim_id": row.get("claim_id", "").strip(),
        "patient_name": (row.get("patient_name") or "").strip() or "Unknown Patient",
        "claim_amount": (row.get("claim_amount") or "").strip() or "0",
        "policy_type": (row.get("policy_type") or "").strip() or "Unknown Policy",
        "reason": row.get("reason", "").strip(),
    }


def load_claims(claims_file: Path = CLAIMS_FILE):
    """Load all claims from the CSV into a dict keyed by upper-cased claim_id.

    Malformed rows (missing claim_id or reason) are skipped rather than raising,
    since a single bad row in a hand-edited CSV shouldn't crash the whole app.
    """
    if not claims_file.exists():
        raise ClaimLoadError(f"Claims file not found: {claims_file}")

    claims = {}

    try:
        with claims_file.open(mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames or not set(REQUIRED_FIELDS).issubset(set(reader.fieldnames)):
                raise ClaimLoadError(
                    f"Claims file is missing required columns. Expected: {REQUIRED_FIELDS}"
                )

            for row in reader:
                if not _row_is_usable(row):
                    continue
                normalized = _normalize_row(row)
                claims[normalized["claim_id"].upper()] = normalized
    except csv.Error as exc:
        raise ClaimLoadError(f"Could not parse claims file: {exc}") from exc

    return claims


def get_claim(claim_id: str, claims_file: Path = CLAIMS_FILE):
    """Look up a single claim by ID (case-insensitive, whitespace-tolerant).

    Returns None if the claim ID is blank or not found.
    """
    if not claim_id or not claim_id.strip():
        return None

    claims = load_claims(claims_file)
    return claims.get(claim_id.strip().upper())
