import os
import jwt
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from fastapi.security import OAuth2PasswordBearer

# vars
pwd = CryptContext(schemes=["bcrypt"])
secret_key = os.getenv("SECRET_KEY")
alg = os.getenv("ALGORITHM")
expires_in = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


# ----- PASSWORD METHODS -----
def hash_password(pword: str) -> str:
    return pwd.hash(pword)

def verify_password(attempt: str, hashed: str) -> bool:
    return pwd.verify(attempt, hashed)


# ----- JWT METHODS ------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_jwt(payload: dict):
    expire =  datetime.now(timezone.utc)
    expire += timedelta(minutes = expires_in)
    payload["exp"] = expire

    return jwt.encode(payload, secret_key, algorithm=alg)

def verify_jwt(token: str):
    return jwt.decode(token, secret_key, algorithms=[alg])