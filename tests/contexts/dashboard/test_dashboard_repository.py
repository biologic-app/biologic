from src.infrastructure.repositories.dashboard import _postgres_period


def test_postgres_period_maps_api_period_values() -> None:
    assert _postgres_period("daily") == "day"
    assert _postgres_period("weekly") == "week"
    assert _postgres_period("monthly") == "month"
