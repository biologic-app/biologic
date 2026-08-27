"""Canonical permission catalogue owned by the backend.

The database stores assignments for these codes; it is not allowed to invent
permission names at runtime through the public API.
"""

PERMISSION_CODES: frozenset[str] = frozenset(
    {
        "directions.read", "directions.create", "directions.update", "directions.delete",
        "directions.register", "directions.import", "directions.release",
        "samples.read", "samples.create", "samples.update", "samples.delete",
        "samples.register", "samples.reject", "samples.close", "samples.import",
        "research.read", "research.create", "research.update", "research.delete",
        "research.confirm", "research.start", "research.complete", "research.reject",
        "tests.read", "tests.create", "tests.update", "tests.delete",
        "tests.start", "tests.complete", "tests.reject", "tests.requeue",
        "protocols.read", "protocols.create", "protocols.update", "protocols.delete",
        "protocols.issue", "protocols.release",
        "conclusions.read", "conclusions.create", "conclusions.update", "conclusions.delete",
        "users.read",
        "users.create",
        "users.update",
        "users.delete",
        "roles.read",
        "roles.create",
        "roles.update",
        "roles.delete",
        "roles.assign",
        "permissions.read",
        "role_permissions.read",
        "role_permissions.update",
        "user_scopes.read",
        "user_scopes.update",
        "workflows.read",
        "workflows.create",
        "workflows.update",
        "workflows.delete",
        "workflows.register",
        "workflows.import",
        "workflows.confirm",
        "workflows.start",
        "workflows.complete",
        "workflows.reject",
        "workflows.requeue",
        "workflows.close",
        "workflows.issue",
    }
)


def is_registered(code: str) -> bool:
    return code in PERMISSION_CODES
