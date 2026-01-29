from datetime import UTC,datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
import jwt

from pwdlib import PasswordHash
from config import settings


password_hasher = PasswordHash.recommended() # The password hasher that is recommended by pwdlib

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/token") # The OAuth2PasswordBearer instance extracts the token from the header contained in the user login endpoint.


def password_hash(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
            to_encode, 
            settings.secret_key.get_secret_value(), 
            algorithm=settings.algorithm
        )
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    """ Verify the access token and return the user_id if valid or None if invalid"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms = [settings.algorithm],
            options ={"require": ["exp", "sub"]}

        )
    except jwt.InvalidTokenError:
            return None
    else:
        return payload.get("sub")
        


