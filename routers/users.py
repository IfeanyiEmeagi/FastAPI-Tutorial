from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import UserCreate, UserResponse, UserUpdate, PostResponse 

import models

router = APIRouter()

@router.post(
    "",
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


# Get user
@router.get(
    "/{user_id}",
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

# Update user
@router.patch(
    "/{user_id}",
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


@router.delete(
    "/{user_id}",
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


# Get User posts
@router.get(
    "/{user_id}/posts",
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