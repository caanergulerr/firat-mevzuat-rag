"""
rag_pipeline.py
---------------
Uçtan uca RAG pipeline: soru → retrieval → generation → kaynaklı cevap.

Kullanım:
    pipeline = RAGPipeline()
    result = pipeline.ask("Mazeret sınavı için GPA şartı var mı?")
    print(result["answer"])
    print(result["sources"])
"""

import logging
import time
from dataclasses import dataclass, field

from backend.retriever import MevzuatRetriever
from backend.generator import generate_answer

logger = logging.getLogger(__name__)

# Düşük skor eşiği — bu değerin altındaki sonuçlar görmezden gelinir
MIN_RELEVANCE_SCORE = 0.4


@dataclass
class RAGResult:
    """RAG pipeline'ının tek bir sorguya verdiği yanıtı temsil eder."""
    question: str
    answer: str
    sources: list[str]
    model: str
    retrieved_chunks: list = field(default_factory=list)
    latency_ms: float = 0.0
    num_chunks_retrieved: int = 0


class RAGPipeline:
    """
    Fırat Mevzuat dijital asistan pipeline'ı.

    1. Soruyu BERTurk ile encode et
    2. ChromaDB'den en ilgili k chunk'ı al (semantik arama)
    3. Düşük skorlu chunk'ları filtrele
    4. LLM ile kaynaklı cevap üret
    """

    def __init__(self, top_k: int = 5, min_score: float = MIN_RELEVANCE_SCORE):
        self.top_k = top_k
        self.min_score = min_score
        self.retriever = MevzuatRetriever()

    def ask(self, question: str) -> RAGResult:
        """
        Öğrencinin sorusuna cevap verir.

        Args:
            question: Doğal dil sorusu (Türkçe)

        Returns:
            RAGResult — cevap, kaynaklar ve metrikler
        """
        start = time.time()
        logger.info(f"Soru işleniyor: '{question}'")

        # 1. Retrieval
        chunks = self.retriever.retrieve(question, top_k=self.top_k)

        # 2. Alaka düzeyi filtreleme
        relevant_chunks = [c for c in chunks if c.score >= self.min_score]

        if not relevant_chunks:
            logger.warning(f"Hiçbir chunk eşiği geçemedi (min_score={self.min_score}). Ham chunk sayısı: {len(chunks)}")

        # 3. Cevap üretimi
        gen_result = generate_answer(question, relevant_chunks)

        latency = round((time.time() - start) * 1000, 1)

        return RAGResult(
            question=question,
            answer=gen_result["answer"],
            sources=gen_result["sources"],
            model=gen_result["model"],
            retrieved_chunks=relevant_chunks,
            latency_ms=latency,
            num_chunks_retrieved=len(relevant_chunks),
        )

    def is_ready(self) -> bool:
        """Pipeline'ın sorguya hazır olup olmadığını kontrol eder."""
        return self.retriever.is_ready()


if __name__ == "__main__":
    pipeline = RAGPipeline()

    if not pipeline.is_ready():
        print("⚠️  Önce indexleme yapın: python scripts/embed_and_index.py")
    else:
        questions = [
            "Mazeret sınavı hakkı ne zaman kullanılabilir?",
            "Çift anadal için GPA şartı nedir?",
            "Öğrenci kayıt dondurabilir mi?",
        ]
        for q in questions:
            result = pipeline.ask(q)
            print(f"\n{'='*60}")
            print(f"Soru: {result.question}")
            print(f"Cevap: {result.answer[:300]}...")
            print(f"Kaynaklar: {', '.join(result.sources)}")
            print(f"Süre: {result.latency_ms}ms | Chunk sayısı: {result.num_chunks_retrieved}")
