"""Текущий пользователь."""
CREATOR_ID = 1  # veronika

_current_user_id = None


def current_user_id() -> int:
    global _current_user_id
    if _current_user_id is None:
        _current_user_id = CREATOR_ID
    return _current_user_id
