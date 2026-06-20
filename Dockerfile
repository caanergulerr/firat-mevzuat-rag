# ===== Fırat Mevzuat RAG — Hugging Face Spaces Docker =====
# 16 GB RAM, 2 vCPU — ML modelleri rahatlıkla çalışır

FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları (önce kopyala — Docker cache için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu
COPY backend/ ./backend/

# Veri dosyaları (embedding index + BM25 chunk'ları)
COPY chroma_db/ ./chroma_db/
COPY data/processed/chunks.json ./data/processed/chunks.json

# HF Spaces port 7860 kullanır
ENV PORT=7860
EXPOSE 7860

# Sunucuyu başlat
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "7860"]
