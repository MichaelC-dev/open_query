from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, func

# ----- USER TABLE DEFINITION -----
class Users(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, max_length=255)
    hashed_password: str
    date_created: datetime = Field(default_factory = func.now)


# ----- USER I/O INTERFACES -----
class UserCreate(SQLModel):
    username: str
    password: str
    confirm_password: str

class UserLogin(SQLModel):
    username: str
    password: str

class UserUpdate(SQLModel):
    new_username: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None
    # changes can only be confirmed if `old_password` is valid
    old_password: Optional[str] = None