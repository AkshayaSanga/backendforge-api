import mimetypes
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.token import UploadedFile
from app.models.user import User


ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


class FileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload(self, file: UploadFile, user: User) -> UploadedFile:
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"File type '{content_type}' is not allowed")

        contents = await file.read()
        if len(contents) > MAX_SIZE_BYTES:
            raise ValueError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

        ext = Path(file.filename or "file").suffix
        stored_name = f"{uuid.uuid4().hex}{ext}"
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / stored_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)

        record = UploadedFile(
            user_id=user.id,
            original_filename=file.filename or stored_name,
            stored_filename=stored_name,
            content_type=content_type,
            size_bytes=len(contents),
            storage_path=str(file_path),
        )
        self.db.add(record)
        await self.db.flush()
        return record
