from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, func, Session, select
from src.models.documents import Documents

# ----- RAGS TABLE DEFINITION -----
class Rags(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=255)
    date_created: datetime = Field(default_factory = func.now)
    public: bool = Field(default=False)
    # relations
    user_id: int = Field(foreign_key="users.id")


# ----- RAGS I/O INTERFACES -----
class RagCreate(SQLModel):
    name: str
    # desc: Optional[str] = None
    public: Optional[bool] = None

class RagQuery(SQLModel):
    message: str
    temperature: Optional[float] = None

class RagUpdate(SQLModel):
    name: Optional[str] = None
    # desc: Optional[str] = None
    public: Optional[bool] = None


# ----- HELPERS -----
def to_json(rag: Rags, session: Session) -> dict[str, str]:
    obj = {
        "id": rag.id,
        "name": rag.name,
        "public": rag.public,
        "user_id": rag.user_id,
        "created": rag.date_created,
    }
    documents = []
    
    # fetch docs
    db_docs = session.exec(
        select(Documents).where(Documents.rag_id == rag.id)
    ).all()
    for db_doc in db_docs:
        curr_doc = {
            "doc_id": db_doc.id,
            "original_name": db_doc.original_file_name,
            "size": db_doc.file_length,
            "file_type": db_doc.file_type,
            "status": db_doc.status
        }
        documents.append(curr_doc)
    
    obj["documents"] = documents
    return obj