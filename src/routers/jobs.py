import src.utils as utils
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.password import oauth2_scheme
from src.app import get_session
from src.models.jobs import Jobs, Citations
from src.models.documents import Documents, Chunks
from src.utils.jwt import user_from_token

router = APIRouter(prefix="/jobs")


@router.get("/{id}")
def get_job(
    id: int,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
):
    user = user_from_token(token, session)

    # ensure that the job ID exists, and that it belongs to user
    selected_job = session.exec(
        select(Jobs)
        .where(Jobs.id == id)
        .where(Jobs.user_id == user.id)
    ).first()
    if selected_job is None:
        raise HTTPException(400, f"Job '{id}' is forbidden/ does not exist.")
    
    # aggregate citations
    citations_db = session.exec(
        select(Citations).where(Citations.job_id == selected_job.id)
    ).all()
    citations = []
    for citation in citations_db:
        result = render_citation(citation, session)
        citations.append(result)

    # aggregate and return job data.
    response = {
        "query": selected_job.query,
        "status": selected_job.status,
        "response": selected_job.response,
        "RAG ID": selected_job.rag_id,
        "citations": citations
    }
    return response


# ----- HELPER -----
def render_citation(cites: Citations | None, session: Session) -> str:
    if cites is None: return None
    ret = {}

    # get doc details
    selected_doc: Documents = session.exec(
        select(Documents)
        .where(Documents.id == cites.doc_id)
    ).first()
    if selected_doc:
        ret["filename"] = selected_doc.original_file_name
    
    # get chunk details
    selected_chunk: Chunks = session.exec(
        select(Chunks)
        .where(Chunks.id == cites.chunk_id)
    ).first()
    if selected_chunk:
        ret["page_no"] = selected_chunk.page_number
        ret["contents"] = selected_chunk.content

    return ret