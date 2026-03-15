import json
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from climbers_journal.routers.chat import router as chat_router  # noqa: E402

app = FastAPI(title="Climbers Journal", version="0.1.0")

origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
