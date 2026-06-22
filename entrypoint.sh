#!/bin/bash
# ============================================================
# entrypoint.sh — HF Spaces başlatma betiği
# ChromaDB bozuksa / boşsa otomatik olarak yeniden indexler.
# ============================================================
set -e

CHROMA_DB_PATH="${CHROMA_DB_PATH:-./chroma_db}"
CHUNKS_PATH="./data/processed/chunks.json"
COLLECTION_NAME="${CHROMA_COLLECTION_NAME:-firat_mevzuat}"

echo "=========================================="
echo " Fırat Mevzuat RAG — Başlatılıyor..."
echo "=========================================="

# Yardımcı fonksiyon: ChromaDB sağlıklı mı?
check_index() {
    python3 - <<'PYEOF'
import sys, os
os.environ.setdefault("CHROMA_DB_PATH", "./chroma_db")
os.environ.setdefault("CHROMA_COLLECTION_NAME", "firat_mevzuat")
try:
    import chromadb
    client = chromadb.PersistentClient(path=os.getenv("CHROMA_DB_PATH"))
    col = client.get_collection(name=os.getenv("CHROMA_COLLECTION_NAME"))
    count = col.count()
    if count > 0:
        print(f"INDEX_OK:{count}")
        sys.exit(0)
    else:
        print("INDEX_EMPTY")
        sys.exit(1)
except Exception as e:
    print(f"INDEX_ERROR:{e}")
    sys.exit(1)
PYEOF
}

# Index'i kontrol et; bozuk veya boşsa yeniden oluştur
echo "[1/3] ChromaDB index kontrol ediliyor..."

INDEX_STATUS=$(check_index 2>&1 || true)
echo "  → Durum: $INDEX_STATUS"

if echo "$INDEX_STATUS" | grep -q "INDEX_OK"; then
    COUNT=$(echo "$INDEX_STATUS" | grep -oP '(?<=INDEX_OK:)\d+')
    echo "  ✅ Index hazır ($COUNT chunk)"
else
    echo "  ⚠️  Index bozuk veya boş — yeniden oluşturuluyor..."

    # Bozuk chroma_db klasörünü temizle
    if [ -d "$CHROMA_DB_PATH" ]; then
        echo "[2/3] Eski (bozuk) chroma_db temizleniyor..."
        rm -rf "$CHROMA_DB_PATH"
    fi

    if [ ! -f "$CHUNKS_PATH" ]; then
        echo "  ❌ HATA: $CHUNKS_PATH bulunamadı! Image yanlış oluşturulmuş."
        exit 1
    fi

    echo "[2/3] Embedding indexleme başlatılıyor (bu ~2-5 dk sürebilir)..."
    python3 scripts/embed_and_index.py
    echo "  ✅ Indexleme tamamlandı!"
fi

echo "[3/3] FastAPI sunucusu başlatılıyor (port: ${PORT:-7860})..."
exec uvicorn backend.api:app --host 0.0.0.0 --port "${PORT:-7860}"
