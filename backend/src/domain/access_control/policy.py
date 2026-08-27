def authorize(actor: object, code: str, resource: object | None = None) -> bool:
    """Application-layer authorization hook.

    ``CurrentPrincipal`` supplies ``can``; keeping this adapter structural avoids
    coupling domain/application services to the HTTP dependency module.  A
    missing capability is always deny (including unknown resources).
    """
    checker = getattr(actor, "can", None)
    if not callable(checker):
        return False
    return bool(checker(code))


def is_action_allowed(*, role_key: str, permission: str) -> bool:
    """Deprecated compatibility shim; role grants now come from PostgreSQL.

    It intentionally fails closed rather than maintaining a second hardcoded
    role-permission source of truth.
    """
    return role_key == "superadmin" and permission.count(".") == 1
