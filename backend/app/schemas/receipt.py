"""Receipt schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class ReceiptUrlOut(BaseModel):
    url: str
    expires_at: datetime
