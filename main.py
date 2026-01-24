from typing import Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

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

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

from typing import Annotated

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts, "title": "Home"
        }
    )


@app.get("/post/{post_id}", include_in_schema=False, name="post_page")
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
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
async def user_posts(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    result = await db.execute(
        select(models.Post)
        .selectinload(models.Post.author)
        .where(models.Post.user_id == user_id)
    )
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
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check for duplicate username
    result = await db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    if result.scalars().first():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"User with username: {user.username} already exists."
        )

    # Check for duplicate email
    result = await db.execute(
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
    await db.commit()
    await db.refresh(new_user)

    return new_user


@app.delete(
    "/api/user/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Fetch the user frmom the db
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    await db.delete(user)
    await db.commit()
    

# Update user
@app.patch(
    "/api/user/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
async def update_user(user_id: int, user_data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    
    # Fetch the user frmom the db
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Check if the new username or email already exists
    
    if user_data.username is not None and user_data.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == user_data.username)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with username: {user_data.username} already exists."
            )

    if user_data.email is not None and user_data.email != user.email:
        result = db.execute(
            select(models.User).where(models.User.email == user_data.email)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email: {user_data.email} already exists."
            )

    # Update the user
    new_user_data = user_data.model_dump(exclude_unset=True)
    for field, value in new_user_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@app.get(
    "/api/user/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
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
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check if the user exists
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Get user posts
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id),
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
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts

@app.post("/api/post", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check if the user exists
    result = await  db.execute(
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
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@app.get("/api/post/{post_id}", response_model=PostResponse, status_code=status.HTTP_200_OK)
async def get_post(post_id: int, db   : Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id),
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
async def full_post_update(post_id: int, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check if the post exists
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id),
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
        result = await db.execute(
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

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


# Partial post update
@app.patch(
    "/api/post_update/{post_id}",
    response_model=PostResponse,
)
async def partial_post_update(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check if the post exists
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id),
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

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

# Delete post
@app.delete(
    "/api/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check if the post exists
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id),
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found."
        )

    await db.delete(post)
    await db.commit()




@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):

    if request.url.path.startswith("/api"):
        return await http_exception_handler (request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
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
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

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