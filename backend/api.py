"""
api.py
------
FastAPI REST API — frontend ve dış istemciler için.

Çalıştırma:
    uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000

Endpoint'ler:
    POST /query   — Soru sor, cevap + kaynaklar al
    GET  /health  — Sistem durumu
    GET  /docs    — Otomatik Swagger UI (FastAPI tarafından oluşturulur)
"""

import logging
from datetime import datetime
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Uygulama ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fırat Mevzuat RAG API",
    description="Fırat Üniversitesi yönetmeliklerini NLP ve RAG ile sorgulayan dijital asistan.",
    version="1.0.0",
)

# CORS — frontend'in farklı port'tan istek atabilmesi için
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy Pipeline ─────────────────────────────────────────────────────────────
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from backend.rag_pipeline import RAGPipeline
        _pipeline = RAGPipeline()
    return _pipeline


# ── Veri Modelleri ─────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, example="Mazeret sınavı hakkım var mı?")
    top_k: int = Field(default=5, ge=1, le=10)


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    model: str
    latency_ms: float
    num_chunks: int
    timestamp: str
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    index_ready: bool
    message: str


# ── Cache Yardımcı Fonksiyon ──────────────────────────────────────────────────
@lru_cache(maxsize=100)
def get_cached_answer(question: str):
    """Soruyu pipeline'a iletir; aynı soru tekrar gelirse LLM'e gitmeden cache'den döner."""
    pipeline = get_pipeline()
    return pipeline.ask(question)


# ── Endpoint'ler ───────────────────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse, summary="Yönetmelik sorusu sor")
async def query(request: QueryRequest):
    """
    Öğrencinin sorusunu alır, bağlamda bulunan yönetmelik maddelerine göre yanıtlar.
    Her cevap hangi maddeye dayandığını belirtir.
    """
    try:
        pipeline = get_pipeline()

        if not pipeline.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Sistem hazır değil. Lütfen önce 'python scripts/embed_and_index.py' çalıştırın.",
            )

        hits_before = get_cached_answer.cache_info().hits
        result = get_cached_answer(request.question)
        was_cached = get_cached_answer.cache_info().hits > hits_before

        return QueryResponse(
            question=result.question,
            answer=result.answer,
            sources=result.sources,
            model=result.model,
            latency_ms=result.latency_ms,
            num_chunks=result.num_chunks_retrieved,
            timestamp=datetime.utcnow().isoformat(),
            cached=was_cached,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query hatası: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sunucu hatası: {str(e)}")


@app.get("/health", response_model=HealthResponse, summary="Sistem durumu")
async def health():
    """ChromaDB index'inin hazır olup olmadığını kontrol eder."""
    try:
        pipeline = get_pipeline()
        ready = pipeline.is_ready()
        return HealthResponse(
            status="ok" if ready else "degraded",
            index_ready=ready,
            message="Sistem hazır." if ready else "Index bulunamadı. Lütfen embed_and_index.py çalıştırın.",
        )
    except Exception as e:
        return HealthResponse(status="error", index_ready=False, message=str(e))


@app.get("/", summary="API kök")
async def root():
    return {
        "message": "Fırat Mevzuat RAG API çalışıyor.",
        "docs": "/docs",
        "query_endpoint": "/query",
    }
