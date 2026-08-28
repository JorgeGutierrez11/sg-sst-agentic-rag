from agents.consulta_normativa.langchain_rag.business_context.profile import (
    update_business_profile,
)


def test_adds_explicit_user_data_to_empty_profile() -> None:
    profile = {}

    result = update_business_profile(
        current_profile=profile,
        updates={
            "economic_activity": "Mantenimiento y reparación de motocicletas",
            "worker_count": 8,
        },
        source="user_explicit",
    )

    assert result == {
        "economic_activity": "Mantenimiento y reparación de motocicletas",
        "worker_count": 8,
    }


def test_overwrites_existing_value_with_new_explicit_value() -> None:
    profile = {
        "worker_count": 8,
        "risk_class": "I",
    }

    result = update_business_profile(
        current_profile=profile,
        updates={"worker_count": 10},
        source="user_explicit",
    )

    assert result["worker_count"] == 10
    assert result["risk_class"] == "I"


def test_accepts_verified_derived_information() -> None:
    profile = {
        "ciiu_code": "1240",
    }

    result = update_business_profile(
        current_profile=profile,
        updates={"risk_class": "I"},
        source="verified_derived",
    )

    assert result == {
        "ciiu_code": "1240",
        "risk_class": "I",
    }


def test_rejects_invalid_worker_count() -> None:
    profile = {
        "worker_count": 8,
    }

    result = update_business_profile(
        current_profile=profile,
        updates={"worker_count": -3},
        source="user_explicit",
    )

    assert result["worker_count"] == 8


def test_rejects_boolean_as_worker_count() -> None:
    profile = {}

    result = update_business_profile(
        current_profile=profile,
        updates={"worker_count": True},
        source="user_explicit",
    )

    assert "worker_count" not in result


def test_rejects_invalid_risk_class() -> None:
    profile = {
        "risk_class": "I",
    }

    result = update_business_profile(
        current_profile=profile,
        updates={"risk_class": "BAJO"},
        source="user_explicit",
    )

    assert result["risk_class"] == "I"


def test_rejects_empty_string_values() -> None:
    profile = {
        "economic_activity": "Fabricación de calzado",
        "ciiu_code": "1523",
    }

    result = update_business_profile(
        current_profile=profile,
        updates={
            "economic_activity": "",
            "ciiu_code": "   ",
        },
        source="user_explicit",
    )

    assert result["economic_activity"] == "Fabricación de calzado"
    assert result["ciiu_code"] == "1523"


def test_does_not_mutate_original_profile() -> None:
    profile = {
        "worker_count": 8,
    }

    result = update_business_profile(
        current_profile=profile,
        updates={"worker_count": 10},
        source="user_explicit",
    )

    assert profile["worker_count"] == 8
    assert result["worker_count"] == 10