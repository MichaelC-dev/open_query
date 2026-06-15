import os
from pathlib import Path
from ollama import Client
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from typing import Optional

# ----- VARS -----
ollama_url = os.getenv("OLLAMA_URL")
if ollama_url is None:
    ollama_url = 'http://ollama:11434' #fallback 
client = Client(host=ollama_url)


# ----- EXPOSED FUNCTIONS -----
def embed_pdf(pdf_path: str):
    reader = PdfReader(pdf_path)
    embeddings_data = []

    # loop through each page to extract text
    for index, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip(): continue # skip empty pages
        curr_embeddings = embed(text, page_no=index+1)
        embeddings_data += curr_embeddings
    return embeddings_data

def embed_txt(txt_path: str):
    text = Path(txt_path).read_text(encoding="utf-8")
    return embed(text)


# ----- HELPERS -----
def embed(text: str, page_no: Optional[int] = None):
    # partition page text into discrete chunks
    text_splits = split_text(text)

    # call ollama, and extract the vector from the response
    embeddings_data = []
    embed_model_name = os.getenv("EMBED_MODEL")
    for text in text_splits:
        response = client.embed(model=embed_model_name, input=text)
        vector = response["embeddings"][0]
        payload = {"text": text, "embedding": vector}
        if page_no is not None:
            payload["page"] = page_no
        embeddings_data.append(payload)

    return embeddings_data

def split_text(text, chunk_size=1024):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=50,
        length_function=len
    )
    return text_splitter.split_text(text)