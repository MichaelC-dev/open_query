import os
from pathlib import Path
from sqlmodel import Session
from src.models.documents import Documents, Chunks
from src.services.embedders import embed_pdf, embed_txt

def ingest(doc_id, engine):
    with Session(engine) as session:
        doc = session.get(Documents, doc_id)
        if doc is None:
            raise Exception(f"Document '{doc_id}' does not exist")

        doc.status = "processing"
        session.add(doc)
        session.commit()
        session.refresh(doc)
    
    # fetch file, and ensure that exists in the file system
    dir = os.getenv("DOC_LOCATION")
    if not dir: raise Exception("DOC_LOCATION is not configured")
    file_name = f"{doc.stored_key}.{doc.file_type}"
    file_name = os.path.join(dir, file_name)
    
    file_path = Path(file_name)
    if not file_path.is_file():
        raise Exception(f"Document file '{file_path}' does not exist")
    
    # TODO - this should be cleaned up
    # dispatch embeddings based on file type
    if doc.file_type == "pdf":
        result = embed_pdf(str(file_path))
    elif doc.file_type == "txt":
        result = embed_txt(str(file_path))
    else:
        raise Exception(f"type '{doc.file_type}' could not be resolved.")

    # commit to DB
    with Session(engine) as session:
        try:
            for chunk in result: commit_page(chunk, doc, session)
            doc.status = "uploaded"
            session.add(doc)
            session.commit()
        except Exception as e:
            doc.status = "error"
            session.add(doc)
            session.commit()
            raise e


# ----- HELPERS -----
def commit_page(chunk, doc: Documents, session: Session):
    '''
    Pre: `page` adopts the same structure
    as a given `dict` produced by `embed`.
    '''
    try:
        db_chunk = Chunks(
            page_number=chunk["page"],
            content=chunk["text"],
            embedding=chunk["embedding"],
            document_id=doc.id,
            rag_id=doc.rag_id
        )
        session.add(db_chunk)
        session.commit()
        session.refresh(db_chunk)
    except Exception as e: raise e