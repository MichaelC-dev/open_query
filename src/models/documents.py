from datetime import datetime
from sqlmodel import SQLModel, Field, func
from uuid import UUID
from typing import Any
from pgvector.sqlalchemy import VECTOR


# ----- DOCUMENTS TABLE DEFINITION -----
class Documents(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uploaded_at: datetime = Field(default_factory = func.now)
    original_file_name: str = Field(max_length=255, nullable=False)
    stored_key: UUID = Field(unique=True, nullable=False)
    file_length: int = Field()
    status: str = Field(max_length=255, nullable=False)
    user_id: int = Field(foreign_key="users.id")
    rag_id: int = Field(foreign_key="rags.id")


class Chunks(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory = func.now)
    content: str = Field(max_length=1024, nullable=False)
    page_number: int = Field(nullable=False)
    embedding: Any = Field(sa_type=VECTOR(768))
    document_id: int = Field(foreign_key="documents.id")
    rag_id: int = Field(foreign_key="rags.id")
