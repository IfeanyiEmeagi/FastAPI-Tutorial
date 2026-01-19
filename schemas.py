from pydantic import BaseModel, Field, EmailStrConfigDict


class UserBase(BaseMoadel):
    email: EmailStr = Field(max_length=50)
    username: str = Field(max_length=50)


class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_file: str | None
    image_path: str

class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    user_id: int

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    post_date: str
    author: UserResponse

    
