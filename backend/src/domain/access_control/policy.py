ROLE_PERMISSIONS: dict[str, set[str]] = {
    "developer": {"*"},
    "registrar": {
        "directions.create",
        "directions.update",
        "directions.register",
        "directions.import",
        "samples.create",
        "samples.update",
        "samples.register",
        "samples.reject",
    },
    "lab_doctor": {
        "research.confirm",
        "research.start",
        "research.reject",
        "tests.start",
        "tests.result",
        "tests.requeue",
        "tests.reject",
        "samples.reject",
    },
    "lab_chief": {
        "research.confirm",
        "research.start",
        "research.reject",
        "research.add_tests",
        "tests.start",
        "tests.result",
        "tests.requeue",
        "tests.reject",
        "samples.reject",
        "samples.close",
    },
    "lab_assistant": {"research.read", "tests.read"},
    "branch_chief": {"directions.read", "samples.read", "alerts.read"},
    "sanitary_inspector": {"directions.read", "samples.read", "protocols.read"},
    "user_admin": {
        "users.*",
        "roles.*",
        "permissions.*",
        "user_scopes.*",
        "role_subscription_rules.*",
    },
}


def is_action_allowed(*, role_key: str, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(role_key, set())
    resource = permission.split(".", maxsplit=1)[0]
    return "*" in permissions or f"{resource}.*" in permissions or permission in permissions
