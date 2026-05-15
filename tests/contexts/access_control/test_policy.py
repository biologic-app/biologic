from src.contexts.access_control.domain.policy import is_action_allowed


def test_developer_has_global_wildcard() -> None:
    assert is_action_allowed(role_key="developer", permission="tests.result")


def test_registrar_can_register_samples() -> None:
    assert is_action_allowed(role_key="registrar", permission="samples.register")


def test_lab_assistant_cannot_complete_tests() -> None:
    assert not is_action_allowed(role_key="lab_assistant", permission="tests.result")
