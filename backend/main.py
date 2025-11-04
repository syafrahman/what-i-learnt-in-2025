import asyncio
import os
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dotenv import load_dotenv
from openai import OpenAI

from database import get_db, init_db
from models import Submission


class SubmissionPayload(BaseModel):
    text: str = Field(..., min_length=1, max_length=280)
    name: Optional[str] = Field(default=None, max_length=120)


MODERATION_PROMPT = (
    """You are a content moderator for 'What I Learnt in 2025'.\n"""
    """Approve if the text is reflective, neutral, or positive.\n"""
    """Reject if it includes hate speech, sexual content, personal data, spam, or meaningless text.\n"""
    """Respond only with APPROVE or REJECT.\n"""
)


class RateLimiter:
    def __init__(self, cooldown_seconds: int) -> None:
        self.cooldown = cooldown_seconds
        self._usage_map: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> tuple[bool, float]:
        async with self._lock:
            now = time.monotonic()
            last = self._usage_map.get(key)
            if last is not None and now - last < self.cooldown:
                retry_after = self.cooldown - (now - last)
                return False, retry_after
            self._usage_map[key] = now
            return True, 0.0


rate_limiter = RateLimiter(cooldown_seconds=60)


def get_client_ip(request: Request) -> str:
    if forwarded := request.headers.get("x-forwarded-for"):
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def check_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    allowed, retry_after = await rate_limiter.allow(ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {int(retry_after) + 1} seconds.",
        )


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


load_dotenv()
app = FastAPI(title="What I Learnt in 2025 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_client: Optional[OpenAI] = None


@app.on_event("startup")
async def on_startup() -> None:
    global openai_client
    await init_db()
    openai_client = get_openai_client()


async def moderate_text(text: str) -> str:
    if openai_client is None:
        raise HTTPException(status_code=503, detail="Moderation service unavailable.")

    payload = f"{MODERATION_PROMPT}\nSubmission: {text.strip()}"

    loop = asyncio.get_running_loop()

    def call_openai() -> str:
        response = openai_client.responses.create(
            model="gpt-4o-mini",
            input=payload,
        )
        return response.output_text.strip().upper()

    try:
        decision = await loop.run_in_executor(None, call_openai)
    except Exception as exc:  # pragma: no cover - network failures
        raise HTTPException(status_code=503, detail="Moderation service unavailable.") from exc

    if decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=503, detail="Unexpected moderation response.")

    return decision


@app.post("/api/submit", dependencies=[Depends(check_rate_limit)])
async def submit(payload: SubmissionPayload, db: AsyncSession = Depends(get_db)):
    submission = Submission(
        text=payload.text.strip(),
        name=payload.name.strip() if payload.name else None,
    )
    db.add(submission)
    await db.flush()

    decision = await moderate_text(submission.text)
    submission.status = "approved" if decision == "APPROVE" else "rejected"

    await db.commit()
    await db.refresh(submission)

    return {"id": submission.id, "status": submission.status}


@app.get("/api/feed")
async def feed(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Submission)
        .where(Submission.status == "approved")
        .order_by(Submission.created_at.desc())
        .limit(100)
    )
    results = await db.execute(stmt)
    items = results.scalars().all()
    return [
        {
            "text": item.text,
            "name": item.name,
            "date": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@app.get("/api/random")
async def random_submission(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Submission)
        .where(Submission.status == "approved")
        .order_by(func.random())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="No submissions available.")
    return {
        "text": record.text,
        "name": record.name,
        "date": record.created_at.isoformat() if record.created_at else None,
    }


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
