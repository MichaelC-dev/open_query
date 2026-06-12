from sqlmodel import Session, select
from jwt import InvalidTokenError, ExpiredSignatureError
from fastapi import HTTPException
from src.models.users import Users
from src.password import verify_jwt

def user_from_token(token: str, session: Session) -> Users:
    '''
    Given a JWT, ensure that the JWT is correct, and that
    it points to a user who is currently in a session.
    '''
    # extract dict from JWT
    user_details = None
    try:
        user_details = verify_jwt(token)
    except InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(400, "Expired.")
    if user_details is None:
        raise HTTPException(401, "Invalid token.")

    # extract username from `user_details["sub"]`
    uname = user_details.get("sub")
    if uname is None:
        raise HTTPException(401, "Invalid token.")
    
    # query DB for `username`
    selected_user = session.exec(
        select(Users).where(Users.username == uname)
    ).first()
    if selected_user is None:
        raise HTTPException(400, f"matched user '{uname}' does not exist.")
    return selected_user