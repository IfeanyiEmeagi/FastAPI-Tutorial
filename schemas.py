from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr = Field(max_length=50)
    username: str = Field(min_length=1,max_length=50)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if isinstance(v, str) else v


class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=50)
    username: str | None = Field(default=None, min_length=1, max_length=50)
    image_file: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str | None) -> str | None:
        return v.lower() if isinstance(v, str) else v

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    image_file: str | None
    image_path: str

class UserPrivate(UserPublic):
    email: EmailStr


class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    user_id: int         # Temporary - 


class Token(BaseModel):
    access_token: str
    token_type: str


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserPublic

    
