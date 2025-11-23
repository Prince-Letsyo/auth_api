from datetime import datetime, timezone
from typing import Any, Protocol, cast
from sqlalchemy import Connection, event
from sqlalchemy.orm import Mapper, Session

from app.schemas.user_schemas import ProfileModel, UserModel


class Auditable(Protocol):
    created_at: datetime | None
    updated_at: datetime | None


@event.listens_for(Session, "before_flush")
def receive_before_flush(
    session: Session,
    _flush_context: Any,  # pyright: ignore[reportExplicitAny, reportAny]
    _instances: Any,  # pyright: ignore[reportAny, reportExplicitAny]
):
    for raw in session.new:  # pyright: ignore[reportAny]
        obj = cast(Auditable, raw)
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)

    for raw in session.dirty:  # pyright: ignore[reportAny]
        obj = cast(Auditable, raw)
        if hasattr(obj, "updated_at"):
            obj.updated_at = datetime.now(timezone.utc)


@event.listens_for(UserModel, "after_insert")
def create_profile(
    _mapper: Mapper[UserModel], connection: Connection, target: UserModel
):
    """
    Automatically creates a profile as soon as the User is inserted.
    Runs inside the transaction.
    """

    _ = connection.execute(  # pyright: ignore[reportUnknownVariableType]
        ProfileModel.__table__.insert().values(user_id=target.id)  # pyright: ignore[reportAttributeAccessIssue, reportUnknownArgumentType, reportUnknownMemberType]
    )  
