"""
retriever.py
------------
ChromaDB üzerinden semantik arama motoru.

Kullanım:
    retriever = MevzuatRetriever()
    results = retriever.retrieve("Mazeret sınavı şartları neler?", top_k=5)
"""

import os
import logging
from dataclasses import dataclass

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Bir arama sonucunu temsil eder."""
    text: str
    regulation_name: str
    article_no: str
    article_title: str
    source_file: str
    score: float  # Cosine similarity (0-1 arası, yüksek = daha ilgili)

    def citation(self) -> str:
        """Kaynak gösterimi: 'Lisans Yönetmeliği, Madde 5'"""
        return f"{self.regulation_name}, Madde {self.article_no}"


class MevzuatRetriever:
    """
    Öğrenci sorusuna en ilgili yönetmelik maddelerini bulan sınıf.
    ChromaDB + BERTurk tabanlı semantik arama kullanır.
    """

    def __init__(
        self,
        chroma_db_path: str = None,
        collection_name: str = None,
        embedding_model: str = None,
    ):
        self.chroma_db_path = chroma_db_path or os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.collection_name = collection_name or os.getenv("CHROMA_COLLECTION_NAME", "firat_mevzuat")
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "dbmdz/bert-base-turkish-cased")

        self._client = None
        self._collection = None

    def _init_db(self):
        """Lazy initialization — ilk sorguda bağlanır."""
        if self._collection is not None:
            return

        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model,
            device=os.getenv("EMBEDDING_DEVICE", "cpu"),
        )
        self._client = chromadb.PersistentClient(path=self.chroma_db_path)
        self._collection = self._client.get_collection(
            name=self.collection_name,
            embedding_function=embedding_fn,
        )
        count = self._collection.count()
        logger.info(f"ChromaDB bağlantısı kuruldu. ({count} chunk mevcut)")

    def retrieve(self, query: str, top_k: int = None) -> list[RetrievedChunk]:
        """
        Sorguya en yakın chunk'ları döner.

        Args:
            query: Öğrencinin sorusu (Türkçe doğal dil)
            top_k: Kaç sonuç isteniyor (varsayılan: .env'den)

        Returns:
            Benzerlik skoruna göre sıralı RetrievedChunk listesi
        """
        self._init_db()

        if top_k is None:
            top_k = int(os.getenv("TOP_K_RESULTS", 5))

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance → similarity (1 - distance)
            score = round(1 - dist, 4)
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    regulation_name=meta.get("regulation_name", "Bilinmiyor"),
                    article_no=meta.get("article_no", "?"),
                    article_title=meta.get("article_title", ""),
                    source_file=meta.get("source_file", ""),
                    score=score,
                )
            )

        logger.info(f"'{query[:40]}...' → {len(chunks)} sonuç (en yüksek skor: {chunks[0].score if chunks else 0})")
        return chunks

    def is_ready(self) -> bool:
        """ChromaDB ve index'in hazır olup olmadığını kontrol eder."""
        try:
            self._init_db()
            return self._collection.count() > 0
        except Exception:
            return False


if __name__ == "__main__":
    retriever = MevzuatRetriever()

    if not retriever.is_ready():
        print("⚠️  Index hazır değil. Önce: python scripts/embed_and_index.py")
    else:
        test_query = "Mazeret sınavı için hangi belgeler gerekli?"
        results = retriever.retrieve(test_query, top_k=3)
        print(f"\nSoru: {test_query}\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] Skor: {r.score:.3f} | {r.citation()}")
            print(f"     {r.text[:200]}...\n")
