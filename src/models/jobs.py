from datetime import datetime
from sqlmodel import SQLModel, Field, func


# ----- JOBS TABLE DEFINITION -----
class Jobs(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory = func.now)
    query: str = Field(nullable=False, max_length=50)
    temperature: float = Field(nullable=False)
    response: str = Field(nullable=False, default="[empty]")
    status: str = Field(nullable=False, default="pending")
    # relations
    user_id: int = Field(foreign_key="users.id")
    rag_id: int = Field(foreign_key="rags.id")


class Citations(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory = func.now)
    job_id: int = Field(foreign_key="jobs.id")
    doc_id: int = Field(foreign_key="documents.id")
    chunk_id: int = Field(foreign_key="chunks.id")