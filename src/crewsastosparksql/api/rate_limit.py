import uuid
from datetime import datetime
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.auth import get_current_user


def check_rate_limit(current_user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.utcnow()

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
            detail=f"Monthly limit ({current_user.monthly_request_limit}) exceeded. Try again next month.",
        )

    usage.request_count += 1
    db.commit()

    return {
        "X-RateLimit-Limit": str(current_user.monthly_request_limit),
        "X-RateLimit-Remaining": str(current_user.monthly_request_limit - usage.request_count),
    }
