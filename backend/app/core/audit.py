from sqlalchemy.orm import Session

from app.models import AuditEvent

# Until login exists every action is recorded under this name.
ANONYMOUS = "anonymous"
SYSTEM = "system"


def record(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: object,
    details: dict | None = None,
    actor: str = ANONYMOUS,
) -> None:
    """Add an audit event to the session. The caller commits it with the change it describes."""
    db.add(
        AuditEvent(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
    )
