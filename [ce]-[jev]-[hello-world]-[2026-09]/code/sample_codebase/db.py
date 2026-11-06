"""db.py — Lightweight database access layer (SQLite for the demo)."""

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "app.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_user(username: str) -> dict | None:
    """Fetch a user record by username."""
    conn   = get_connection()
    cursor = conn.execute(f"SELECT * FROM users WHERE username = '{username}'")
    row    = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_orders_for_user(user_id: int, status: str = "all") -> list[dict]:
    """Fetch orders for a given user, optionally filtered by status."""
    conn = get_connection()
    if status == "all":
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ?", (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM orders WHERE user_id = {user_id} AND status = '{status}'"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, email: str, hashed_password: str) -> int:
    """Insert a new user and return the new row id."""
    conn   = get_connection()
    cursor = conn.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hashed_password),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id
