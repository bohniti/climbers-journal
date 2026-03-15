from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from climbers_journal.db import get_session
from climbers_journal.services.import_csv import import_climbing_csv

router = APIRouter(tags=["import"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class ImportRowError(BaseModel):
    row: int
    reason: str


class ImportResponse(BaseModel):
    created: int
    skipped: int
    rows_imported: int
    errors: list[ImportRowError]


@router.post("/import/climbing-csv", response_model=ImportResponse)
async def upload_climbing_csv(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
):
    if file.content_type and file.content_type not in (
        "text/csv",
        "application/octet-stream",
        "text/plain",
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Expected CSV file, got {file.content_type}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    text = content.decode("utf-8")
    result = await import_climbing_csv(session, text)
    return result
