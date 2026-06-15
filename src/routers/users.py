from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.models.users import Users, UserCreate, UserLogin, UserUpdate
from src.password import hash_password, verify_password
from src.password import create_jwt, oauth2_scheme
from src.utils.jwt import user_from_token
from src.utils.users import update_username
from src.db import get_session

router = APIRouter(prefix="/user")


@router.post("/")
async def create(
    credentials: UserCreate,
    session: Session = Depends(get_session)
):
    # ensure that `credentials.username` is unique
    user_exists = session.exec(
        select(Users).where(Users.username == credentials.username)
    ).first()
    if user_exists: raise HTTPException(400, f"username taken.")
    
    new_user = Users(
        username = credentials.username,
        hashed_password = hash_password(credentials.password)
    )
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return f"Created user '{new_user.username}'"
    except Exception as e: raise HTTPException(400, e)


@router.get("/")
async def read(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    selected_user = user_from_token(token, session)

    payload = {
        "id": selected_user.id,
        "name": selected_user.username,
        "created": selected_user.date_created
    }
    return payload


@router.patch("/")
async def update(
    details: UserUpdate,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    selected_user = user_from_token(token, session)
     
    # ensure that `old_password` hashes to the current password.
    pw = details.old_password
    attempt = verify_password(pw, selected_user.hashed_password)
    if not attempt: raise HTTPException(400, f"Incorrect password provided.")

    status = []
    # if `new_username` is set, verify that is unique and update.
    if details.new_username is not None:
        try:
            result = update_username(selected_user, details.new_username, session)
            status.append(result)
        except Exception as e:
            raise HTTPException(500, f"could not update credentials: {e}")

    # if `new_password` is set, update.
    if details.new_password is not None:
        if details.new_password != details.confirm_password:
            raise HTTPException(400, f"passwords did not match.")
        selected_user.hashed_password = hash_password(details.new_password)
        status.append("Updated password.")
    
    # commit
    try:
        session.add(selected_user)
        session.commit()
    except Exception as e:
        raise HTTPException(500, f"Could not update details: {e}")

    status.append("Succesful changes. Log in again to receive a new token.")
    return status


@router.delete("/")
async def delete(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
):
    selected_user = user_from_token(token, session)
    
    name = selected_user.username
    session.delete(selected_user)
    session.commit()

    return f"deleted user '{name}'"


@router.post("/login")
async def login(credentials: UserLogin, session: Session = Depends(get_session)):
    try: 
        selected_user = session.exec(
            select(Users)
            .where(Users.username == credentials.username)
        ).first()
    except Exception as e: raise HTTPException(400, e)

    # verify credentials
    if selected_user is None:
        raise HTTPException(400, f"User '{credentials.username}' does not exist.")
    attempt = verify_password(credentials.password, selected_user.hashed_password)
    if not attempt:
        raise HTTPException(400, f"User '{credentials.username}' does not exist.")
    
    # create and return JWT
    payload = { "sub": selected_user.username }
    token = create_jwt(payload)
    return {
        "token_type": "bearer",
        "token": token
    }