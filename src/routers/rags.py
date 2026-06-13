import os
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session, select
from typing import List
from src.app import get_session
from src.models.documents import Documents
from src.models.rags import Rags, RagCreate, RagUpdate, RagQuery, to_json
from src.models.jobs import Jobs
from src.password import oauth2_scheme
from src.utils.jwt import user_from_token
from src.worker.dispatch import enqueue_document, enqueue_query

router = APIRouter(prefix="/rags")


@router.post("/")
async def create(
    details: RagCreate,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    user = user_from_token(token, session)

    # collate RAG details
    rag = Rags(
        name=details.name,
        public=details.public or False,
        user_id=user.id
    )

    # commit
    try:
        session.add(rag)
        session.commit()
        session.refresh(rag)
    except Exception as e:
        raise HTTPException(400, str(e))
    
    return f"created RAG {details.name} ({rag.id})"


@router.get("/{id}")
async def read(
    id: int,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    user = user_from_token(token, session)

    rag = session.get(Rags, id)
    if rag is None: raise HTTPException(404, "RAG not found")
    if not rag.public and rag.user_id != user.id:
        raise HTTPException(403, "Access denied")

    return to_json(rag)


@router.get("/")
async def read_all(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    user = user_from_token(token, session)

    rags = session.exec(
        select(Rags)
        .where((Rags.public == True) | (Rags.user_id == user.id))
    ).all()

    ret = []
    for rag in rags: ret.append(to_json(rag))
    return ret


@router.patch("/{id}")
async def update(
    id: int,
    details: RagUpdate,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    user = user_from_token(token, session)

    rag = session.get(Rags, id)
    if rag is None: raise HTTPException(404, "RAG not found")
    if rag.user_id != user.id:
        raise HTTPException(403, "You do not own this RAG")

    if details.name is not None:
        # ensure that details.name is unique
        query = select(Rags).where(Rags.name == details.name)
        matching_name = session.exec(query).first()
        if matching_name is not None:
            raise HTTPException(400, f"Name '{details.name}' is already taken.")
        rag.name = details.name
    if details.public is not None:
        rag.public = details.public

    try:
        session.add(rag)
        session.commit()
        session.refresh(rag)
    except Exception as e:
        raise HTTPException(500, str(e))
    return "RAG updated"


@router.delete("/{id}")
async def delete(
    id: int,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    user = user_from_token(token, session)
    # TODO - remove documents from disk

    rag = session.get(Rags, id)
    if rag is None: raise HTTPException(404, "RAG not found")
    if rag.user_id != user.id:
        raise HTTPException(403, "You do not own this RAG")
    
    name = rag.name
    try:
        session.delete(rag)
        session.commit()
    except Exception as e:
        raise HTTPException(500, str(e))
    return f"Deleted RAG '{name}'"


# QUERY
@router.post("/query/{id}")
async def query_rag(
    id: int, 
    query: RagQuery,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)       
):
    user = user_from_token(token, session)

    # ensure that RAG is valid
    selected_rag = session.get(Rags, id)
    if selected_rag is None:
        raise HTTPException(404, f"RAG {id} does not exist.")
    # ensure that RAG is public, or belongs to user
    belongs_to_user = (selected_rag.user_id == user.id)
    if not (belongs_to_user or selected_rag.public):
        raise HTTPException(403, f"Forbidden from using RAG {selected_rag.id}.")

    # ensure that temperature is a float
    temperature = query.temperature
    if temperature is None:
        temperature = 0.3 # default temp
    if not isinstance(temperature, float):
        raise HTTPException(400, "Temperature must be a float.")
    if not (0 <= temperature <= 1):
        raise HTTPException(400, "temperature must be between 0 and 1.") 
    
    # create Job, and commit to DB
    new_job = Jobs(
        query=query.message,
        temperature=temperature,
        user_id=user.id,
        rag_id=selected_rag.id
    )
    try:
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
    except Exception as e: raise HTTPException(500, e)

    # enqueue query job, and return
    enqueue_query(new_job.id)
    return {
        "id": new_job.id,
        "query": new_job.query,
        "temperature": new_job.temperature,
        "status": new_job.status
    }


# INGEST DOCUMENTS
@router.post("/ingest/{id}")
async def ingest_docs(
    id: int,
    files: List[UploadFile] | None,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)   
):
    user = user_from_token(token, session)
    rag = sanitise_ingestion(id, files, user.id, session)

    doc_dir = os.getenv("DOC_LOCATION")
    doc_root = Path(doc_dir)
    doc_root.mkdir(parents=True, exist_ok=True)

    created_documents = []
    for file in files:
        file_type = get_permitted_file_type(file)

        # commit file to disk
        file_bytes = await file.read()
        storage_key = uuid4()
        stored_path = doc_root / f"{storage_key}.{file_type}"
        stored_path.write_bytes(file_bytes)

        # commit file to DB
        document = Documents(
            original_file_name=Path(file.filename).name,
            stored_key=storage_key,
            file_length=len(file_bytes),
            file_type=file_type,
            status="pending",
            user_id=user.id,
            rag_id=rag.id,
        )
        try:
            session.add(document)
            session.commit()
            session.refresh(document)
        except Exception as e:
            if stored_path.exists():
                # if the file could not be comitted to the documents table,
                # then it shouldn't dangle on disk.
                stored_path.unlink()
            raise HTTPException(500, str(e))

        # enqueue job
        enqueue_document(document.id)
        
        created_documents.append({
            "id": document.id,
            "original_file_name": document.original_file_name,
            "status": document.status,
        })

    return {
        "rag_id": rag.id,
        "rag_name": rag.name,
        "queued_documents": created_documents,
    }


# ------ HELPERS -----
def sanitise_ingestion(id, files, user_id, session):
    '''
    ensure that the input space is valid,
    and return the RAG correlating to `id`
    '''
    rag = session.get(Rags, id)
    if rag is None: raise HTTPException(404, "RAG not found")
    if rag.user_id != user_id:
        raise HTTPException(403, "You do not own this RAG")

    if files is None: files = []
    if len(files) == 0:
        raise HTTPException(400, "No files were provided")

    doc_dir = os.getenv("DOC_LOCATION")
    if not doc_dir:
        raise HTTPException(500, "DOC_LOCATION is not configured")
    
    max_files = os.getenv("MAX_FILES_UPLOAD")
    if str(max_files).isdigit(): max_files = int(max_files)
    else: max_files = 8 # default
    if len(files) > max_files:
        raise HTTPException(400, f"Upload cannot exceed {max_files} files.")
    
    for file in files:
        file_type = get_permitted_file_type(file)
        if file_type is None:
            msg = f"file '{file.filename}' is not permitted."
            raise HTTPException(403, msg)
        
    return rag


def get_permitted_file_type(file: UploadFile) -> str | None:
    allowed_types = {
        "application/pdf": "pdf",
        "text/plain": "txt"
    }
    return allowed_types.get(file.content_type)