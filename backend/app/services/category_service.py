"""Category business rules, including the default category set."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.category import Category
from app.models.enums import CategoryKind
from app.repositories import category_repository

DEFAULT_EXPENSE_CATEGORIES = [
    "Housing & rent",
    "Food & groceries",
    "Restaurants",
    "Transportation",
    "Utilities",
    "Healthcare",
    "Education",
    "Entertainment",
    "Shopping",
    "Debt repayments",
    "Savings & investments",
    "Personal care",
    "Family expenses",
    "Business expenses",
    "Other expenses",
]

DEFAULT_INCOME_CATEGORIES = [
    "Salary",
    "Freelance income",
    "Business income",
    "Gifts",
    "Interest",
    "Other income",
]


def ensure_defaults(db: Session, user_id: uuid.UUID) -> None:
    """Give a brand-new user a sensible starting set they can rename or delete."""
    if category_repository.count(db, user_id) > 0:
        return

    for kind, names in (
        (CategoryKind.EXPENSE, DEFAULT_EXPENSE_CATEGORIES),
        (CategoryKind.INCOME, DEFAULT_INCOME_CATEGORIES),
    ):
        for name in names:
            db.add(Category(user_id=user_id, name=name, kind=kind, is_system=True))
    db.commit()


def list_categories(db: Session, user_id: uuid.UUID, kind: str | None = None) -> list[Category]:
    ensure_defaults(db, user_id)
    return category_repository.list_for_user(db, user_id, kind)


def get_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> Category:
    category = category_repository.get(db, user_id, category_id)
    if category is None:
        raise APIError(404, "not_found", "Category not found.")
    return category


def _validate_parent(
    db: Session, user_id: uuid.UUID, parent_id: uuid.UUID, kind: CategoryKind
) -> Category:
    parent = category_repository.get(db, user_id, parent_id)
    if parent is None:
        raise APIError(404, "not_found", "Parent category not found.")
    if parent.kind != kind:
        raise APIError(
            422, "category_kind_mismatch", "A subcategory must match its parent's kind."
        )
    if parent.parent_id is not None:
        raise APIError(422, "category_depth", "Only two levels of categories are supported.")
    return parent


def create_category(
    db: Session, user_id: uuid.UUID, name: str, kind: CategoryKind, parent_id: uuid.UUID | None
) -> Category:
    ensure_defaults(db, user_id)

    if parent_id:
        _validate_parent(db, user_id, parent_id, kind)

    if category_repository.name_exists(db, user_id, name, kind.value, parent_id):
        raise APIError(409, "duplicate_category", "A category with that name already exists.")

    category = Category(user_id=user_id, name=name, kind=kind, parent_id=parent_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID, changes: dict) -> Category:
    category = get_category(db, user_id, category_id)

    if "parent_id" in changes:
        new_parent = changes["parent_id"]
        if new_parent == category.id:
            raise APIError(422, "category_cycle", "A category cannot be its own parent.")
        if new_parent is not None:
            _validate_parent(db, user_id, new_parent, category.kind)
            if category.children:
                raise APIError(
                    422, "category_depth", "Move its subcategories first; only two levels are allowed."
                )

    if "name" in changes and changes["name"]:
        parent_id = changes.get("parent_id", category.parent_id)
        if category_repository.name_exists(
            db, user_id, changes["name"], category.kind.value, parent_id, exclude_id=category.id
        ):
            raise APIError(409, "duplicate_category", "A category with that name already exists.")
        category.name = changes["name"]

    if "parent_id" in changes:
        category.parent_id = changes["parent_id"]

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = get_category(db, user_id, category_id)

    if category.children:
        raise APIError(
            409,
            "category_has_children",
            "Delete or move its subcategories before deleting this category.",
        )
    if category_repository.is_in_use(db, user_id, category_id):
        raise APIError(
            409,
            "category_in_use",
            "This category is used by transactions. Reassign them first.",
        )

    db.delete(category)
    db.commit()
