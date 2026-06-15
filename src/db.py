from sqlalchemy import create_engine
import os
from sqlmodel import Session



def construct_engine():
    db_name, db_user, db_password, db_host, db_port = (
        os.getenv("POSTGRES_DB"),
        os.getenv("POSTGRES_USER"),
        os.getenv("POSTGRES_PASSWORD"),
        os.getenv("POSTGRES_HOST"),
        os.getenv("POSTGRES_PORT")
    )

    db_url  = f"postgresql://{db_user}:{db_password}@{db_host}:"
    db_url += f"{db_port}/{db_name}"
    engine = create_engine(db_url)

    return engine


def get_session():
    """Dependency generator for FastAPI to provide DB sessions."""
    engine = construct_engine()
    with Session(engine) as session:
        yield session