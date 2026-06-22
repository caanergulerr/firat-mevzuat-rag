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

# Indexleme scripti (entrypoint'te kullanılır)
COPY scripts/embed_and_index.py ./scripts/embed_and_index.py
COPY scripts/__init__.py ./scripts/__init__.py

# Chunk verileri (BM25 + ChromaDB indexleme için gerekli)
COPY data/processed/chunks.json ./data/processed/chunks.json

# NOT: chroma_db bilerek kopyalanmıyor.
# Entrypoint script'i, HF Space'teki ChromaDB versiyonuna uygun
# temiz bir index sıfırdan oluşturuyor.

# Başlatma betiği
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# HF Spaces port 7860 kullanır
ENV PORT=7860
EXPOSE 7860

# Sunucuyu başlat (index kontrolü + uvicorn)
CMD ["./entrypoint.sh"]

