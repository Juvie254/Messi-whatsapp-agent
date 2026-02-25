from fastapi import FastAPI
from contextlib import asynccontextmanager
from webhooks import router as webhook_router
from init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    init_db()
    yield


app = FastAPI(
    title="Inbox Conversion Agent",
    lifespan=lifespan
)

app.include_router(webhook_router)


@app.get("/")
async def health():
    return {"status": "ok"}
