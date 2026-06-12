from sqlalchemy import create_engine
import os


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