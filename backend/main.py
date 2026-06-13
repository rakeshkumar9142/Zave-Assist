from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import api

from dotenv import load_dotenv
load_dotenv()

import os
print("Gemini Key Loaded:", os.getenv("GEMINI_API_KEY"))

app = FastAPI(
    title="Zave Assist API",
    description="AI-powered support platform for Zave",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)


@app.get("/")
async def root():
    return {"message": "Zave Assist API", "docs": "/docs"}
