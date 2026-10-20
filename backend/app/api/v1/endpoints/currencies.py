"""Reference data: supported currencies."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.responses import ok
from app.core.deps import DbSession
from app.models.currency import Currency

router = APIRouter(prefix="/currencies", tags=["reference"])


@router.get("", summary="List supported currencies")
def list_currencies(db: DbSession):
    """Public reference data: ISO code plus how many minor units to format."""
    rows = db.scalars(select(Currency).order_by(Currency.code)).all()
    return ok(
        [
            {"code": row.code, "name": row.name, "decimal_places": row.decimal_places}
            for row in rows
        ]
    )
