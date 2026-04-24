import logging
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Yapılandırma ─────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Fırat Mevzuat RAG API", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pipeline Yükleyici ────────────────────────────────────────────────────────
_pipeline = None

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            from backend.rag_pipeline import RAGPipeline
            _pipeline = RAGPipeline()
            logger.info("RAG Pipeline yüklendi.")
        except Exception as e:
            logger.error(f"Pipeline yükleme hatası: {e}")
            raise HTTPException(status_code=500, detail="Sistem beyni başlatılamadı.")
    return _pipeline

# ── Veri Modelleri (Frontend ile tam uyumlu) ──────────────────────────────────
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)

class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    latency_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# ── Endpoint'ler ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "API Hazır!", "docs": "/docs"}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    try:
        pipeline = get_pipeline()
        
        # Pipeline'dan cevabı al
        result = pipeline.ask(request.question)
        
        # Frontend'in beklediği formatta döndür
        return QueryResponse(
            answer=result.answer,
            sources=result.sources,
            latency_ms=result.latency_ms
        )
    except Exception as e:
        logger.error(f"Sorgu hatası: {e}", exc_info=True)
        # Hata durumunda frontend'in çökmemesi için güvenli bir yanıt dön
        return QueryResponse(
            answer=f"Bir hata oluştu: {str(e)}",
            sources=["Sistem Hatası"],
            latency_ms=0.0
        )