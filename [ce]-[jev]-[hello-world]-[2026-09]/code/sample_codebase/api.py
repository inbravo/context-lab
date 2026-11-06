"""api.py — Simple HTTP handler layer (framework-agnostic for the demo)."""

from auth import require_auth
from db   import get_user, get_orders_for_user


def handle_get_orders(token: str, status: str = "all") -> dict:
    """
    Authenticated endpoint: return orders for the calling user.
    Validates the token, resolves user_id, then queries the DB.
    """
    user_id_str = require_auth(token)
    user        = get_user(user_id_str)
    if user is None:
        return {"error": "User not found", "status": 404}

    orders = get_orders_for_user(user["id"], status=status)
    return {"orders": orders, "count": len(orders), "status": 200}


def handle_health() -> dict:
    """Public endpoint — no auth required."""
    return {"status": "ok"}
