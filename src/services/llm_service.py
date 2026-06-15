from ollama import Client
import os
from sqlmodel import Session, select
from src.models.documents import Documents, Chunks
from src.models.jobs import Jobs, Citations
from src.models.rags import Rags

# ----- VARS -----
UNFORMATTED_PROMPT = """
You are a helpful chat assistant, who specialises in {subject}. A user has asked
you to answer the following question:

{question}.

Using the following sources, answer the question:
"""

# ----- VARS -----
ollama_url = os.getenv("OLLAMA_URL")
if ollama_url is None:
    ollama_url = 'http://ollama:11434' #fallback 
client = Client(host=ollama_url)


DEFAULT_TOP_K = 10
def query(job_id, engine, top_k: int = DEFAULT_TOP_K):
    # fetch job
    job = None
    with Session(engine) as session:
        job = session.get(Jobs, job_id)
    if job is None:
        raise Exception(f"Job {job_id} does not exist.")

    # act on job
    try:
        query_private(job, engine, top_k)
    except Exception as e:
        set_to_error(job, engine)
        raise e


def query_private(job: Jobs, engine, top_k):
    # update status
    with Session(engine) as session:
        job.status = "processing"
        session.add(job)
        session.commit()
        session.refresh(job)

    embed_model_name = os.getenv("EMBED_MODEL")
    embedding = client.embed(model=embed_model_name, input=job.query)
    vector = embedding["embeddings"][0]

    # collect the closest chunks for this RAG directly in SQL using cosine distance
    chunks = []
    with Session(engine) as session:
        try:
            query = (
                select(Chunks)
                .where(Chunks.rag_id == job.rag_id)
                .order_by(Chunks.embedding.op("<=>")(vector))
                .limit(top_k)
            )
            chunks = session.exec(query).all()
        except:
            raise Exception("Could not collect chunks.")
    if chunks is None or chunks == []:
        raise Exception("No Chunks to reference. Try ingesting documents.")
    
    # structure prompt
    selected_rag = None
    with Session(engine) as session:
        selected_rag = session.get(Rags, job.rag_id)
    if selected_rag is None:
        raise Exception("Rag could not be found.")
    rag_name = selected_rag.name
    references = [chunk.content for chunk in chunks]
    prompt = build_prompt(job.query, references, rag_name)

    # fire prompt
    response = client.chat(
        model = os.getenv("LLM_MODEL"),
        messages = [{
            "role": "system",
            "content": prompt
        }],
        options={"temperature": job.temperature}
    )

    # add citations to DB
    for chunk in chunks: add_citation(chunk, job.id, engine)

    # commit success to DB
    message = response["message"]["content"]
    job.status = "completed"
    job.response = message
    with Session(engine) as session:
        session.add(job)
        session.commit()
        session.refresh(job)


# ----- HELPERS -----
def build_prompt(question, references, name):
    prompt = UNFORMATTED_PROMPT
    prompt = prompt.format(question=question, subject=name)
    for reference in references:
        prompt += "\n\n"
        prompt += "'" + str(reference) + "'"
    return prompt

def set_to_error(job: Jobs, engine):
    with Session(engine) as session:
        job.status = "error"
        session.add(job)
        session.commit()
        session.refresh(job)


def add_citation(chunk, job_id, engine):
    new_citation = Citations(
        job_id=job_id,
        chunk_id=chunk.id,
        doc_id=chunk.document_id
    )
    with Session(engine) as session:
        session.add(new_citation)
        session.commit()