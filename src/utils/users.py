from sqlmodel import Session, select
from src.models.users import Users

def update_username(user: Users, new_username: str, session: Session) -> str:
    '''
    Ensures that `user.username` is unique in the the users table. If so, 
    the user model is updated - this method does NOT update the db directly.
    '''
    try: 
        user_exists = session.exec(
            select(Users).where(Users.username == new_username)
        ).first()
    except Exception as e: raise e
    if user_exists is None:
        # mutates
        user.username = new_username
        return f"Changed name to {new_username}."
    return f"User '{new_username}' already exists."