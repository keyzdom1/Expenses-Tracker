"""Versioned API router (/api/v1)."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounts,
    bills,
    budgets,
    categories,
    currencies,
    jobs,
    me,
    notifications,
    receipts,
    recurring,
    reports,
    tags,
    transactions,
)

api_router = APIRouter()
api_router.include_router(currencies.router)
api_router.include_router(me.router)
api_router.include_router(categories.router)
api_router.include_router(accounts.router)
api_router.include_router(transactions.router)
api_router.include_router(tags.router)
api_router.include_router(reports.router)
api_router.include_router(budgets.router)
api_router.include_router(receipts.router)
api_router.include_router(receipts.local_router)
api_router.include_router(recurring.router)
api_router.include_router(bills.router)
api_router.include_router(notifications.router)
api_router.include_router(jobs.router)
