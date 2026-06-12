import ollama
from pypdf import PdfReader
import os
from pathlib import Path
from sqlmodel import Session, select
from src.models.documents import Documents, Chunks

def ingest(doc_id, engine):
    with Session(engine) as session:
        doc = session.get(Documents, doc_id)
        if doc is None:
            raise Exception(f"Document '{doc_id}' does not exist")

        doc.status = "processing"
        session.add(doc)
        session.commit()
        session.refresh(doc)
    
    # fetch file, and ensure that exists in the file_system
    file_name = file_name_from_uuid(doc.stored_key)
    if file_name is None:
        raise Exception("PDF_LOCATION is not configured")
    file_path = Path(file_name)
    if not file_path.is_file():
        raise Exception(f"Document file '{file_path}' does not exist")
    
    # embed file, with `doc` and `doc.rag` as FKs.
    # results are stored page-wise.
    result = embed(str(file_path))
    with Session(engine) as session:
        try:
            for page in result: commit_page(page, doc, session)
            doc.status = "uploaded"
            session.add(doc)
            session.commit()
        except Exception as e:
            doc.status = "error"
            session.add(doc)
            session.commit()
            raise e


def embed(pdf_path: str):
    reader = PdfReader(pdf_path)
    embeddings_data = []

    # loop through each page to extract text
    for index, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip(): continue # skip "empty" pages

        # partition page text into discrete chunks
        text_splits = split_text(text)
        # call ollama, and extract the vector from the response
        embed_model_name = os.getenv("EMBED_MODEL")
        for text in text_splits:
            response = ollama.embed(model=embed_model_name, input=text)
            vector = response["embeddings"][0]
            embeddings_data.append({
                "page": index + 1,
                "text": text,
                "embedding": vector,
            })

    return embeddings_data


def commit_page(page, doc: Documents, session: Session):
    '''
    Pre: `page` adopts the same structure
    as a given `dict` produced by `embed`.
    '''
    try:
        db_chunk = Chunks(
            page_number=page["page"],
            content=page["text"],
            embedding=page["embedding"],
            document_id=doc.id,
            rag_id=doc.rag_id
        )
        session.add(db_chunk)
        session.commit()
        session.refresh(db_chunk)
    except Exception as e: raise e


# ----- HELPERS -----
def file_name_from_uuid(uuid) -> str | None:
    dir = os.getenv("PDF_LOCATION")
    if not dir: return None
    return os.path.join(dir, f"{uuid}.pdf")

def split_text(text, chunk_size=1024):
    return [ # heuristic, but it should be fine
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]