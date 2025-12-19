import hashlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import FileRef, StoredFile, User
from app.schemas import UploadResponse

router = APIRouter(prefix="/files", tags=["files"])


def _storage_root() -> Path:
    return Path(os.getenv("FILE_STORAGE_PATH", "/data/files"))


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    root = _storage_root()
    tmp_dir = root / ".tmp"
    root.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_path = tmp_dir / f"{uuid.uuid4().hex}.upload"
    sha = hashlib.sha256()
    size = 0
    content_type = file.content_type

    try:
        with tmp_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB
                if not chunk:
                    break
                sha.update(chunk)
                out.write(chunk)
                size += len(chunk)
    finally:
        await file.close()

    digest = sha.hexdigest()
    final_path = root / digest

    # 1) 先确保 stored_files 表里有记录（sha256 唯一）
    stored = db.query(StoredFile).filter(StoredFile.sha256 == digest).first()
    dedup_hit = stored is not None

    if not stored:
        stored = StoredFile(
            sha256=digest,
            storage_path=str(final_path),
            size_bytes=size,
            mime_type=content_type,
        )
        db.add(stored)
        try:
            db.commit()
            db.refresh(stored)
        except IntegrityError:
            # 并发情况下别的请求可能刚插入成功：回滚后按“已存在”处理
            db.rollback()
            dedup_hit = True
            stored = db.query(StoredFile).filter(StoredFile.sha256 == digest).first()
            if not stored:
                # 理论上不会发生
                raise HTTPException(status_code=500, detail="Dedup race condition")

    # 2) 落盘：如果文件已存在就删临时；否则把临时文件原子移动到最终路径
    if final_path.exists():
        tmp_path.unlink(missing_ok=True)
    else:
        os.replace(tmp_path, final_path)

    # 3) 为该用户创建引用（同用户重复上传同文件 => 返回已有引用）
    ref = (
        db.query(FileRef)
        .filter(FileRef.user_id == user.id, FileRef.stored_file_id == stored.id)
        .first()
    )
    if not ref:
        ref = FileRef(
            user_id=user.id,
            stored_file_id=stored.id,
            original_filename=file.filename,
        )
        db.add(ref)
        try:
            db.commit()
            db.refresh(ref)
        except IntegrityError:
            db.rollback()
            ref = (
                db.query(FileRef)
                .filter(FileRef.user_id == user.id, FileRef.stored_file_id == stored.id)
                .first()
            )

    return UploadResponse(
        file_id=ref.id,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        dedup=dedup_hit,
    )


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ref = db.query(FileRef).filter(FileRef.id == file_id, FileRef.user_id == user.id).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    stored = ref.stored_file
    path = stored.storage_path
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File missing on disk")

    filename = ref.original_filename or stored.sha256
    return FileResponse(
        path=path,
        filename=filename,
        media_type=stored.mime_type or "application/octet-stream",
    )
