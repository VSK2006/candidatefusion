import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.utils.logger import configure_logging

app = FastAPI(title="CandidateFusion", version="0.1.0")
configure_logging()

# Local dev origins + any deployed frontend origin(s) via env var (comma-separated)
default_origins = ["http://localhost:5173", "http://localhost:4173"]
extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins + extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
