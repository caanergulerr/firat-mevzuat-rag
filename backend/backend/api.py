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
import threading
from datetime import datetime
from functools import lru_cache
import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Lazy Pipeline ─────────────────────────────────────────────────────────────
_pipeline = None
_pipeline_loading = False
_pipeline_error = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from backend.rag_pipeline import RAGPipeline
        _pipeline = RAGPipeline()
    return _pipeline


def _preload_pipeline():
    """Sunucu başladığında pipeline'ı arka planda yükler."""
    global _pipeline, _pipeline_loading, _pipeline_error
    _pipeline_loading = True
    try:
        logger.info("Pipeline arka planda yükleniyor...")
        get_pipeline()
        logger.info("Pipeline hazır!")
    except Exception as e:
        _pipeline_error = str(e)
        logger.error(f"Pipeline yüklenemedi: {e}")
    finally:
        _pipeline_loading = False


# Sunucu başladığında pipeline'ı arka planda yükle
thread = threading.Thread(target=_preload_pipeline, daemon=True)
thread.start()


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


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: str = Field(..., description="'like' veya 'dislike'")


# ── Cache Yardımcı Fonksiyon ──────────────────────────────────────────────────
@lru_cache(maxsize=100)
def get_cached_answer(question: str):
    """Soruyu pipeline'a iletir; aynı soru tekrar gelirse LLM'e gitmeden cache'den döner."""
    pipeline = get_pipeline()
    return pipeline.ask(question)


# ── Endpoint'ler ───────────────────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse, summary="Yönetmelik sorusu sor")
@limiter.limit("5/minute")
def query(request: Request, query_req: QueryRequest):
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
        result = get_cached_answer(query_req.question)
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
def health():
    """ChromaDB index'inin hazır olup olmadığını kontrol eder."""
    # Pipeline henüz yükleniyorsa timeout olmadan hemen cevap ver
    if _pipeline_loading:
        return HealthResponse(
            status="loading",
            index_ready=False,
            message="Model yükleniyor, lütfen bekleyin... (ilk başlatmada ~60 saniye sürebilir)",
        )
    if _pipeline_error:
        return HealthResponse(status="error", index_ready=False, message=_pipeline_error)
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


@app.post("/feedback", summary="Yanıt geri bildirimi (Like/Dislike)")
def submit_feedback(req: FeedbackRequest):
    """Kullanıcının verdiği beğeni veya beğenmeme durumunu kaydeder."""
    try:
        # data/feedback.jsonl dosyasına kaydet
        feedback_dir = os.path.join(os.path.dirname(__dirname__), "data")
        os.makedirs(feedback_dir, exist_ok=True)
        feedback_file = os.path.join(feedback_dir, "feedback.jsonl")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": req.question,
            "answer": req.answer,
            "rating": req.rating
        }
        
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
        logger.info(f"Feedback kaydedildi: {req.rating} (Soru: {req.question[:30]}...)")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Feedback kaydetme hatası: {e}")
        raise HTTPException(status_code=500, detail="Feedback kaydedilemedi.")


@app.get("/ping", summary="Sunucu canlı mı?")
def ping():
    """Pipeline yüklemeden anında cevap verir — liveness probe."""
    return {"status": "alive"}


@app.get("/", summary="API kök")
def root():
    return {
        "message": "Fırat Mevzuat RAG API çalışıyor.",
        "docs": "/docs",
        "query_endpoint": "/query",
    }

