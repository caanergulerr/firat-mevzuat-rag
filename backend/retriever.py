"""
retriever.py
------------
Hybrid arama motoru: BM25 (keyword) + ChromaDB (semantic).

BM25 kelime bazlı arama yapar, ChromaDB anlamsal arama.
İkisinin sonuçları birleştirilip en iyi chunk'lar döner.
Bu sayede colloquial (günlük dil) sorular da formal mevzuat
metnine ulaşabilir.

Kullanım:
    retriever = MevzuatRetriever()
    results = retriever.retrieve("Üstten ders alabilir miyim?", top_k=5)
"""

import os
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

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
    Hybrid arama: BM25 (keyword) + ChromaDB (semantic).
    """

    # Not dönüşüm sorguları için anahtar kelime listesi
    DONUSUM_KEYWORDS = [
        "4'lük", "dörtlük", "4 lük", "doertluk", "4lük",
        "100'lük", "yüzlük", "100 lük", "yuzluk",
        "dönüştür", "donustur", "çevir", "cevir",
        "gpa", "not dönüşüm", "karşılık", "karsalik"
    ]
    DONUSUM_CHUNK_ID = "donusum_tablosu_v2"

    def __init__(
        self,
        chroma_db_path: str = None,
        collection_name: str = None,
        embedding_model: str = None,
        chunks_path: str = "data/processed/chunks.json",
    ):
        self.chroma_db_path = chroma_db_path or os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.collection_name = collection_name or os.getenv("CHROMA_COLLECTION_NAME", "firat_mevzuat")
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "dbmdz/bert-base-turkish-cased")
        self.chunks_path = chunks_path

        self._client = None
        self._collection = None

        # BM25 index (lazy init)
        self._bm25 = None
        self._bm25_chunks = None

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

    def _init_bm25(self):
        """BM25 index'i chunks.json'dan oluşturur (bir kez)."""
        if self._bm25 is not None:
            return

        path = Path(self.chunks_path)
        if not path.exists():
            logger.warning(f"BM25 için {self.chunks_path} bulunamadı!")
            return

        with path.open("r", encoding="utf-8") as f:
            self._bm25_chunks = json.load(f)

        # Token: her chunk metnini küçük harfe çevir ve bölümlere ayır
        tokenized = [c["text"].lower().split() for c in self._bm25_chunks]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 index hazırlandı. ({len(self._bm25_chunks)} chunk)")

    def _bm25_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        """BM25 ile keyword tabanlı arama."""
        self._init_bm25()
        if self._bm25 is None:
            return []

        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)

        # En yüksek skorlu top_k chunk'ı al
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        max_score = max(scores[i] for i in top_indices) if top_indices else 1.0

        for idx in top_indices:
            raw_score = scores[idx]
            if raw_score <= 0:
                continue
            normalized = round(raw_score / max(max_score, 1.0), 4)
            chunk_data = self._bm25_chunks[idx]
            results.append(RetrievedChunk(
                text=chunk_data["text"],
                regulation_name=chunk_data.get("regulation_name", "Bilinmiyor"),
                article_no=str(chunk_data.get("article_no", "?")),
                article_title=chunk_data.get("article_title", ""),
                source_file=chunk_data.get("source_file", ""),
                score=normalized,
            ))

        return results

    def retrieve(self, query: str, top_k: int = None) -> list[RetrievedChunk]:
        """
        Hybrid arama: BM25 + Semantic. İkisinin birleşimini döner.

        Args:
            query: Öğrencinin sorusu (Türkçe doğal dil)
            top_k: Kaç sonuç isteniyor

        Returns:
            Benzerlik skoruna göre sıralı RetrievedChunk listesi
        """
        self._init_db()

        if top_k is None:
            top_k = int(os.getenv("TOP_K_RESULTS", 5))

        # Anahtar kelime kontrolü: Not dönüşüm sorusu mu?
        query_lower = query.lower()
        is_donusum_query = any(k.lower() in query_lower for k in self.DONUSUM_KEYWORDS)

        # --- 1. Semantic Search (ChromaDB) ---
        semantic_top_k = top_k * 2  # Daha fazla aday al, sonra filtrele
        sem_results = self._collection.query(
            query_texts=[query],
            n_results=semantic_top_k,
            include=["documents", "metadatas", "distances"],
        )

        semantic_chunks: dict[str, RetrievedChunk] = {}
        for doc, meta, dist in zip(
            sem_results["documents"][0],
            sem_results["metadatas"][0],
            sem_results["distances"][0],
        ):
            score = round(1 - dist, 4)
            chunk_id = f"{meta.get('source_file', '')}_{meta.get('article_no', '')}"
            semantic_chunks[chunk_id] = RetrievedChunk(
                text=doc,
                regulation_name=meta.get("regulation_name", "Bilinmiyor"),
                article_no=meta.get("article_no", "?"),
                article_title=meta.get("article_title", ""),
                source_file=meta.get("source_file", ""),
                score=score,
            )

        # --- 2. BM25 Search ---
        bm25_results = self._bm25_search(query, top_k=top_k * 2)
        bm25_chunks: dict[str, RetrievedChunk] = {}
        for c in bm25_results:
            chunk_id = f"{c.source_file}_{c.article_no}"
            bm25_chunks[chunk_id] = c

        # --- 3. Hybrid Merge (RRF - Reciprocal Rank Fusion) ---
        # Her chunk için hybrid skor = 0.6 * semantic + 0.4 * bm25
        all_ids = set(semantic_chunks.keys()) | set(bm25_chunks.keys())
        merged: list[tuple[float, RetrievedChunk]] = []

        for cid in all_ids:
            sem_score = semantic_chunks[cid].score if cid in semantic_chunks else 0.0
            bm25_score = bm25_chunks[cid].score if cid in bm25_chunks else 0.0
            hybrid_score = round(0.6 * sem_score + 0.4 * bm25_score, 4)

            # Hangi chunk'ı kullanalım? Semantic varsa onu, yoksa BM25'i
            chunk = semantic_chunks.get(cid) or bm25_chunks[cid]
            chunk.score = hybrid_score
            merged.append((hybrid_score, chunk))

        # Skora göre sırala, en iyi top_k al
        merged.sort(key=lambda x: x[0], reverse=True)
        chunks = [c for _, c in merged[:top_k]]

        # --- 4. Not Dönüşüm Tablosu Intercept ---
        donusum_included = any(
            "donusum" in c.regulation_name.lower() or self.DONUSUM_CHUNK_ID in c.source_file
            for c in chunks
        )
        if is_donusum_query and not donusum_included:
            logger.info("Not dönüşüm sorgusu tespit edildi — tablo ekleniyor.")
            try:
                tablo_result = self._collection.get(
                    ids=[self.DONUSUM_CHUNK_ID],
                    include=["documents", "metadatas"],
                )
                if tablo_result["documents"]:
                    tablo_chunk = RetrievedChunk(
                        text=tablo_result["documents"][0],
                        regulation_name=tablo_result["metadatas"][0].get("regulation_name", "Not Donusum Tablosu"),
                        article_no="1",
                        article_title="Doertluk Sisteminden Yuzluk Sisteme Donusum",
                        source_file=tablo_result["metadatas"][0].get("source_file", "1606909297.pdf"),
                        score=0.99,
                    )
                    chunks.insert(0, tablo_chunk)
                    chunks = chunks[:top_k]
            except Exception as e:
                logger.warning(f"Donusum tablosu eklenemedi: {e}")

        logger.info(
            f"Hybrid arama: '{query[:40]}' → {len(chunks)} sonuç "
            f"(en yüksek skor: {chunks[0].score if chunks else 0})"
        )
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
        test_queries = [
            "Üstten ders alabilir miyim?",
            "Çift anadal şartları nelerdir?",
            "Mazeret sınavı için hangi belgeler gerekli?",
        ]
        for q in test_queries:
            results = retriever.retrieve(q, top_k=5)
            print(f"\nSoru: {q}")
            for i, r in enumerate(results, 1):
                print(f"  [{i}] Skor: {r.score:.3f} | {r.citation()}")
                print(f"       {r.text[:150]}...")
