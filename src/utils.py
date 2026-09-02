from datetime import timezone


def ensure_tz(dt):
    """Đảm bảo datetime có timezone (mặc định UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
