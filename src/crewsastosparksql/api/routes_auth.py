import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.auth import (
    hash_password,
    verify_password,
    generate_api_key,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    api_key: str
    monthly_request_limit: int
    is_active: bool
    created_at: str


class UsageResponse(BaseModel):
    current_month_usage: int
    monthly_limit: int
    remaining: int


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if db.query(db_models.User).filter(db_models.User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = db_models.User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        api_key=generate_api_key(),
        monthly_request_limit=1000,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        api_key=db_user.api_key,
        monthly_request_limit=db_user.monthly_request_limit,
        is_active=db_user.is_active,
        created_at=db_user.created_at.isoformat()
    )


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(db_models.User).filter(db_models.User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: db_models.User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        api_key=current_user.api_key,
        monthly_request_limit=current_user.monthly_request_limit,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/usage", response_model=UsageResponse)
def get_usage(current_user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime
    now = datetime.utcnow()
    usage = db.query(db_models.Usage).filter(
        db_models.Usage.user_id == current_user.id,
        db_models.Usage.year == now.year,
        db_models.Usage.month == now.month
    ).first()

    current_usage = usage.request_count if usage else 0
    return UsageResponse(
        current_month_usage=current_usage,
        monthly_limit=current_user.monthly_request_limit,
        remaining=max(0, current_user.monthly_request_limit - current_usage)
    )


@router.post("/regenerate-api-key", response_model=UserResponse)
def regenerate_api_key(current_user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.api_key = generate_api_key()
    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        api_key=current_user.api_key,
        monthly_request_limit=current_user.monthly_request_limit,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )
