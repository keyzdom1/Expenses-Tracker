"""Bill listing, payment and skipping."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.enums import BillStatus
from app.models.recurring import Bill
from app.repositories import bill_repository
from app.schemas.transaction import TransactionCreate
from app.services import transaction_service


def serialize(bill: Bill) -> dict:
    recurring = bill.recurring
    return {
        "id": str(bill.id),
        "recurring_id": str(bill.recurring_id),
        "due_date": bill.due_date.isoformat(),
        "amount_minor": bill.amount_minor,
        "currency_code": bill.currency_code,
        "status": bill.status.value,
        "paid_transaction_id": (
            str(bill.paid_transaction_id) if bill.paid_transaction_id else None
        ),
        "type": recurring.type.value,
        "vendor": recurring.vendor,
        "description": recurring.description,
        "account_name": recurring.account.name,
        "destination_account_name": (
            recurring.destination_account.name if recurring.destination_account else None
        ),
        "category_name": recurring.category.name if recurring.category else None,
    }


def list_bills(db: Session, user_id: uuid.UUID, **filters) -> list[dict]:
    return [serialize(bill) for bill in bill_repository.list_bills(db, user_id, **filters)]


def _locked_bill(db: Session, user_id: uuid.UUID, bill_id: uuid.UUID) -> Bill:
    bill = db.scalar(
        select(Bill)
        .where(Bill.id == bill_id, Bill.user_id == user_id)
        .with_for_update()
    )
    if bill is None:
        raise APIError(404, "not_found", "Bill not found.")
    return bill


def pay_bill(db: Session, user_id: uuid.UUID, bill_id: uuid.UUID) -> dict:
    bill = _locked_bill(db, user_id, bill_id)

    if bill.status in (BillStatus.PAID, BillStatus.SKIPPED):
        raise APIError(409, "bill_already_settled", "This bill is already paid or skipped.")

    recurring = bill.recurring
    payload = TransactionCreate(
        type=recurring.type,
        amount_minor=bill.amount_minor,
        account_id=recurring.account_id,
        dest_account_id=recurring.dest_account_id,
        category_id=recurring.category_id,
        transaction_date=bill.due_date,
        payment_method=recurring.payment_method,
        vendor=recurring.vendor,
        description=recurring.description,
    )
    body, _ = transaction_service.create_transaction(db, user_id, payload)

    bill.status = BillStatus.PAID
    bill.paid_transaction_id = uuid.UUID(body["data"]["id"])
    db.commit()
    db.refresh(bill)

    return serialize(bill)


def skip_bill(db: Session, user_id: uuid.UUID, bill_id: uuid.UUID) -> dict:
    bill = _locked_bill(db, user_id, bill_id)

    if bill.status in (BillStatus.PAID, BillStatus.SKIPPED):
        raise APIError(409, "bill_already_settled", "This bill is already paid or skipped.")

    bill.status = BillStatus.SKIPPED
    db.commit()
    db.refresh(bill)

    return serialize(bill)
