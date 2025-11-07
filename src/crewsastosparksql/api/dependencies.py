import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.utils.auth import get_secret_key, ALGORITHM

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> db_models.User:
    if api_key:
        user = db.query(db_models.User).filter(db_models.User.api_key == api_key).first()
        if user and user.is_active:
            return user

    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = db.query(db_models.User).filter(db_models.User.id == user_id).first()
                if user and user.is_active:
                    return user
        except JWTError:
            pass

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def check_rate_limit(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)

    usage = db.query(db_models.Usage).filter(
        db_models.Usage.user_id == current_user.id,
        db_models.Usage.year == now.year,
        db_models.Usage.month == now.month
    ).first()

    if not usage:
        usage = db_models.Usage(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            year=now.year,
            month=now.month,
            request_count=0
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)

    if usage.request_count >= current_user.monthly_request_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit ({current_user.monthly_request_limit}) exceeded"
        )

    usage.request_count += 1
    db.commit()

    return {
        "X-RateLimit-Limit": str(current_user.monthly_request_limit),
        "X-RateLimit-Remaining": str(current_user.monthly_request_limit - usage.request_count)
    }
