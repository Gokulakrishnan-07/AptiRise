from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.admin import AuditLog
from app.models.user import User


def log_admin_action(
    db: Session,
    admin: User,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[str] = None,
    request: Optional[Request] = None
):
    ip = None
    if request:
        client = request.client
        ip = client.host if client else None

    entry = AuditLog(
        admin_id=admin.id,
        admin_username=admin.username,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        details=details,
        ip_address=ip
    )
    db.add(entry)
    db.commit()
