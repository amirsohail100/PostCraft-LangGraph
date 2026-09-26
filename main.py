import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from schema.payload import GenerateRequest, GenerateResponse
from agent import run_writer

app = FastAPI(title="PostCraft Writer-Reviewer API")

# Har request me 2-8+ LLM calls chain hoti hain (writer + reviewer, upto 3
# attempts, upto 2 search rounds), isliye limit kaafi strict rakhi hai.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Dev ke time frontend alag origin se call kar sake, isliye CORS open rakha hai.
# Production me isko apne actual frontend domain tak restrict kar dena.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 3 requests per minute, per IP - is endpoint ka cost sabse zyada hai is family me.
@app.post("/api/generate", response_model=GenerateResponse)
@limiter.limit("3/minute")
def generate(request: Request, payload: GenerateRequest):
    if not payload.topic.strip():
        raise HTTPException(status_code=400, detail="topic khaali hai")

    try:
        result = run_writer(payload.topic)
    except Exception as exc:  # Mistral/Groq/Tavily API errors, etc.
        raise HTTPException(status_code=502, detail=str(exc))

    return GenerateResponse(**result)


# Frontend (index.html/style.css/script.js) ko isi FastAPI server se serve karo.
# Ye line hamesha sabse aakhir me honi chahiye, kyunki ye "/" ko catch-all bana deti hai.
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
