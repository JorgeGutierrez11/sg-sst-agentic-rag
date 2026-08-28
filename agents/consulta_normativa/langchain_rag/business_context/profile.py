"""Business profile update utilities."""

from typing import Literal

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessProfile,
)


ProfileUpdateSource = Literal[
    "user_explicit",
    "verified_derived",
]


def update_business_profile(
    current_profile: BusinessProfile,
    updates: BusinessProfile,
    source: ProfileUpdateSource,
) -> BusinessProfile:
    """Update the business profile with trusted information.

    Accepted sources:
    - user_explicit: information explicitly provided by the user.
    - verified_derived: information derived and verified from trusted evidence.

    New valid values overwrite previous values.
    """

    updated_profile: BusinessProfile = dict(current_profile)

    if source not in {"user_explicit", "verified_derived"}:
        return updated_profile

    for field, value in updates.items():
        if _is_valid_profile_value(field, value):
            updated_profile[field] = value  # type: ignore[literal-required]

    return updated_profile


def _is_valid_profile_value(field: str, value: object) -> bool:
    """Validate a value before storing it in the business profile."""

    if field == "economic_activity":
        return isinstance(value, str) and bool(value.strip())

    if field == "ciiu_code":
        return isinstance(value, str) and bool(value.strip())

    if field == "worker_count":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
        )

    if field == "risk_class":
        return (
            isinstance(value, str)
            and value.upper() in {"I", "II", "III", "IV", "V"}
        )

    return False