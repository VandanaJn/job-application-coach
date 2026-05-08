from api.config import config


def current_user_id() -> str:
    """Resolves the user_id for the current request.

    Today: returns the single hardcoded user from config (per ADR-006).
    When auth lands: decode a JWT from the Authorization header here —
    every route already takes the result via Depends, so no route changes.
    """
    return config.user_id
