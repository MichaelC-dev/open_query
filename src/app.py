# ----- LOAD .env -----
from dotenv import load_dotenv
load_dotenv()

# ----- INIT DB -----
from sqlmodel import Session
from src.db import construct_engine

engine = construct_engine()
def get_session():
    with Session(engine) as session:
        yield session


# ----- INIT API -----
from fastapi import FastAPI
from threading import Thread
app = FastAPI()
from src.worker.dispatch import Worker, set_worker

worker = Worker(engine)
set_worker(worker)


@app.on_event("startup")
def startup():
    ingestion_worker = Thread(
        target=worker.work,
        daemon=True
    )
    ingestion_worker.start()

# ----- ATTACH ROUTERS -----
from src.routers.users import router as user_router
from src.routers.rags import router as rags_router
from src.routers.jobs import router as jobs_router

app.include_router(user_router)
app.include_router(rags_router)
app.include_router(jobs_router)

@app.get("/")
def health():
    return "Hello, world."