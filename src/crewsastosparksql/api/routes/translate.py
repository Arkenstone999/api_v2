from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from crewsastosparksql.api.dependencies import get_current_user, check_rate_limit
from crewsastosparksql.api import db_models
from crewsastosparksql.api.services.translation_service import TranslationService

router = APIRouter(prefix="/api", tags=["translate"])


class TranslateRequest(BaseModel):
    sas_code: str


class TranslateResponse(BaseModel):
    translated_code: str
    rationale: str
    execution_time_seconds: float
    file_name: str | None = None


@router.post("/translate", response_model=TranslateResponse)
async def translate_code(
    request: TranslateRequest,
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    if not request.sas_code.strip():
        raise HTTPException(status_code=400, detail="SAS code cannot be empty")

    output_dir = str(Path(__file__).parent.parent.parent.parent.parent)
    translation_service = TranslationService(output_dir)

    try:
        job_name = f"quick_{current_user.id}_{uuid.uuid4().hex[:8]}"
        result = translation_service.translate(request.sas_code, job_name)

        return TranslateResponse(
            translated_code=result.code,
            rationale=result.rationale,
            execution_time_seconds=result.execution_time,
            file_name=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/translate/file", response_model=TranslateResponse)
async def translate_file(
    file: UploadFile = File(...),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    if not file.filename or not file.filename.endswith(".sas"):
        raise HTTPException(status_code=400, detail="Only .sas files are accepted")

    try:
        content = await file.read()
        sas_code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 encoded text")

    if not sas_code.strip():
        raise HTTPException(status_code=400, detail="SAS file cannot be empty")

    output_dir = str(Path(__file__).parent.parent.parent.parent.parent)
    translation_service = TranslationService(output_dir)

    try:
        job_name = f"file_{current_user.id}_{uuid.uuid4().hex[:8]}"
        result = translation_service.translate(sas_code, job_name)

        return TranslateResponse(
            translated_code=result.code,
            rationale=result.rationale,
            execution_time_seconds=result.execution_time,
            file_name=file.filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
