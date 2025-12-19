import asyncio
import os

from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, engine
import app.models  # noqa: F401  (确保 models 被导入，create_all 才知道有哪些表)

from app.routers.auth import router as auth_router
from app.routers.files import router as files_router


app = FastAPI(title="SmartCTF FileManager MVP1")
app.include_router(auth_router)
app.include_router(files_router)


@app.on_event("startup")
async def on_startup():
    # 确保存储目录存在
    os.makedirs(os.getenv("FILE_STORAGE_PATH", "/data/files"), exist_ok=True)

    # 等 DB 真正 ready（避免你现在的 connection refused）
    max_tries = int(os.getenv("DB_MAX_TRIES", "60"))
    for i in range(max_tries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception:
            if i == max_tries - 1:
                raise
            await asyncio.sleep(1)

    # DB ready 后再建表
    Base.metadata.create_all(bind=engine)
