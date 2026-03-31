"""
embed_and_index.py
------------------
Hazır chunk'ları BERTurk ile vektöre çevirir ve ChromaDB'ye yazar.

Çalıştırma:
    python scripts/embed_and_index.py

Bu script tamamlandıktan sonra ChromaDB kalıcı olarak disk üzerinde saklanır.
"""

import os
import sys
import json
import logging
from pathlib import Path
from tqdm import tqdm

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Ayarlar
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "dbmdz/bert-base-turkish-cased")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "firat_mevzuat")
BATCH_SIZE = 32

def get_chroma_client() -> chromadb.PersistentClient:
    """ChromaDB kalıcı istemcisi döner."""
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_or_create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """
    ChromaDB collection'ı döner.
    BERTurk sentence-transformer embedding fonksiyonu kullanır.
    """
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        device=os.getenv("EMBEDDING_DEVICE", "cpu"),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},  # Cosine similarity
    )
    return collection

def index_chunks(chunks: list[dict], collection: chromadb.Collection) -> None:
    """
    Chunk listesini ChromaDB'ye batch olarak yazar.
    Var olan chunk'ları günceller (upsert).
    """
    total = len(chunks)
    logger.info(f"{total} chunk indexleniyor (model: {EMBEDDING_MODEL})...")

    for i in tqdm(range(0, total, BATCH_SIZE), desc="Indexleniyor"):
        batch = chunks[i : i + BATCH_SIZE]

        collection.upsert(
            ids=[str(c["chunk_id"]) for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[
                {
                    "regulation_name": str(c.get("regulation_name", "")),
                    "article_no": str(c.get("article_no", "")),
                    "article_title": str(c.get("article_title", "")),
                    "source_file": str(c.get("source_file", "")),
                    "chunk_type": str(c.get("chunk_type", "")),
                }
                for c in batch
            ],
        )

    logger.info(f"✅ {total} chunk başarıyla indexlendi -> '{CHROMA_DB_PATH}'")

def main():
    chunks_path = Path("data/processed/chunks.json")
    if not chunks_path.exists():
        logger.error("data/processed/chunks.json bulunamadı. Önce process_data.py çalıştırın.")
        sys.exit(1)
        
    logger.info(f"Hazır '{chunks_path}' dosyası okunuyor...")
    with chunks_path.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    # ChromaDB'ye yaz
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    index_chunks(chunks, collection)

    # Özet
    count = collection.count()
    logger.info(f"\n📊 ChromaDB'de toplam {count} chunk mevcut.")
    logger.info("🚀 Sistem sorguya hazır! Şimdi 'uvicorn backend.api:app --reload' çalıştırabilirsiniz.")


if __name__ == "__main__":
    main()
