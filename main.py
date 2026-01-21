from typing import Annotated

from fastapi import FastAPI, Request, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db

import models
from schemas import (
    PostResponse, 
    PostCreate,
    UserCreate, 
    UserResponse,
    PostUpdate,
    UserUpdate
)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

from typing import Annotated

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts, "title": "Home"
        }
    )


@app.get("/post/{post_id}", include_in_schema=False, name="post_page")
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    
    title = post.title[:50]
    return templates.TemplateResponse(
            request,
            "post.html",
            {
                "post":post,
                "title": title
            }
        )


@app.get("/user/{user_id}", include_in_schema=False, name="user_posts")
def user_posts(request: Request, user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    user_posts = result.scalars().all()
    
    if not user_posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User has no posts.")
    
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": user_posts,
            "title": f"Posts by {user.username}"
        }
    )


# API Endpoints

@app.post(
    "/api/user",
    response_model=UserResponse,
    status_code = status.HTTP_201_CREATED
)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    # Check for duplicate username
    result = db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    if result.scalars().first():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"User with username: {user.username} already exists."
        )

    # Check for duplicate email
    result = db.execute(
        select(models.User).where(models.User.email == user.email),
    )
    if result.scalars().first():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"User with email: {user.email} already exists."
        )
    
    new_user = models.User(
        username = user.username,
        email = user.email,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.get(
    "/api/user/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return user


# Get User posts
@app.get(
    "/api/user/{user_id}/posts",
    response_model=list[PostResponse],
    status_code=status.HTTP_200_OK
)
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    # Check if the user exists
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Get user posts
    result = db.execute(
        select(models.Post).where(models.Post.user_id == user_id),
    )
    posts = result.scalars().all()
    
    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no posts."
        )
    return posts


# Get all posts
@app.get("/api/posts", response_model=list[PostResponse], status_code=status.HTTP_200_OK)
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts

@app.post("/api/post", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, user_id: int, db: Annotated[Session, Depends(get_db)]):
    # Check if the user exists
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    #Create the post
    new_post = models.Post(
        title = post.title,
        content = post.content,
        user_id = user_id,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get("/api/post/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
def get_post(post_id: int, db   : Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.Post).where(models.Post.id == post_id),
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )
    return post


@app.put(
    "/api/post/{post_id}",
    response_model=PostResponse,
)
def full_post_update(post_id: int,post_data: PostCreate, db: Annotated[Session, Depends(get_db)]):
    # Check if the post exists
    result = db.execute(
        select(models.Post).where(models.Post.id == post_id),
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    # Check if the user is the original poster.
    if post.user_id != post_data.user_id:
        # Check if the user exists
        result = db.execute(
            select(models.User).where(models.User.id == post_data.user_id),
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Update the post
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    db.commit()
    db.refresh(post)
    return post


# Partial post update
@app.patch(
    "/api/post_update/{post_id}",
    response_model=PostResponse,
)
def partial_post_update(post_id: int, post_data: PostUpdate, db: Annotated[Session, Depends(get_db)]):
    # Check if the post exists
    result = db.execute(
        select(models.Post).where(models.Post.id == post_id),
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    post_update = post_data.model_dump(exclude_unset=True)
    for key, value in post_update.items():
        setattr(post, key, value)

    db.commit()
    db.refresh(post)
    return post


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )