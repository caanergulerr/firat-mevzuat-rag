"""
rag_pipeline.py
---------------
Uctan uca RAG pipeline: soru -> query expansion -> retrieval -> generation -> kaynakli cevap.
"""

import os
import logging
import time
from dataclasses import dataclass, field

from backend.retriever import MevzuatRetriever
from backend.generator import generate_answer

logger = logging.getLogger(__name__)

MIN_RELEVANCE_SCORE = 0.1


def _normalize_tr(text: str) -> str:
    """Turkce karakterleri ASCII'ye donusturur — sozluk eslemesi icin."""
    tr_map = {
        'c': 'c', 'g': 'g', 'i': 'i', 's': 's', 'o': 'o', 'u': 'u',
        'C': 'C', 'G': 'G', 'I': 'I', 'S': 'S', 'O': 'O', 'U': 'U',
    }
    result = []
    for ch in text:
        if ch == '\u00e7': result.append('c')    # c
        elif ch == '\u011f': result.append('g')  # g
        elif ch == '\u0131': result.append('i')  # dotless i
        elif ch == '\u015f': result.append('s')  # s
        elif ch == '\u00f6': result.append('o')  # o
        elif ch == '\u00fc': result.append('u')  # u
        elif ch == '\u00c7': result.append('C')  # C
        elif ch == '\u011e': result.append('G')  # G
        elif ch == '\u0130': result.append('I')  # dotted I
        elif ch == '\u015e': result.append('S')  # S
        elif ch == '\u00d6': result.append('O')  # O
        elif ch == '\u00dc': result.append('U')  # U
        else: result.append(ch)
    return ''.join(result)

# Statik arama genisleme sozlugu - Gemini rate limit durumunda fallback
QUERY_DICT = {
    "ustten ders": "ust yariyil ders alma sarti GNO not ortalamasi 3.00 ust yariyildan ders alabilir",
    "ust yariyil": "ust yariyil ders alma sarti GNO not ortalamasi 3.00 ust yariyildan ders alabilir",
    "cift anadal": "cift anadal basvuru kabul sarti GNO not ortalamasi yuzde yirmi basari sirasi kontenjan",
    "yandal": "yandal programa basvuru sarti GNO AKTS kredi",
    "mazeret sinav": "mazeret sinavi hakki basvuru belge saglik raporu haklı gecerli mazeret",
    "kayit dondur": "kayit dondurma izinli ayrilma ogrencilik hakki",
    "mezun olma": "mezuniyet sarti toplam kredi AKTS staj bitirme projesi",
    "not ortalama": "genel not ortalamasi GNO agirlikli ortalama hesaplama",
    "dersten cekil": "ders birakma cekilme kayit silme akademik takvim",
    "staj": "zorunlu staj pratik calisma mezuniyet sarti kredi",
    "disiplin": "disiplin cezasi ogrenci sinav kopya ihlal",
    "burs": "burs basvuru sarti basari kriteri sosyal yardim",
    "yatay gecis": "yatay gecis basvuru sarti kontenjan not ortalamasi",
    "dikey gecis": "dikey gecis basvuru DGS sarti",
    "af": "ogrenci af kanunu egitim ogretim suresi uzatma",
    "sinavdan kaldi": "basarisiz ders tekrar FF DC not",
    "sinif tekrar": "sinif tekrar basarisiz ders yuk GNO",
    # --- Yeni eklenenler ---
    "ust uste":          "azami ogretim suresi ust uste basarisiz donem ilisik kesme kayit silme ogrencilik sona ermesi",
    "kac donem":         "azami ogretim suresi ust uste basarisiz donem ilisik kesme kayit silme",
    "ogrencilik sona":   "azami ogretim suresi ilisik kesme kayit silme ogrencilik sona ermesi",
    "ilisik kesme":      "ilisik kesme kayit silme azami ogretim suresi basarisiz donem",
    "azami sure":        "azami ogretim suresi ust sinir toplam sure donem",
    "muafiyet":          "ders muafiyeti intibak yatay gecis bolum baskanligi yonetim kurulu",
    "not donusum":       "not donusumu ECTS kredi donusum tablosu erasmus yurt disi",
    "erasmus":           "erasmus yurt disi egitim not donusumu ECTS kredi denklik transkript",
    "kayit yenile":      "kayit yenileme donem baslangici akademik takvim borc",
    "devamsizlik":       "devamsizlik yoklama orant yuzde otuz ders devam sarti",
    "ders yuku":         "ders yuku kredi AKTS maksimum sinir donem basarisizligi",
    "transkript":        "transkript not belgesi onaylı resmi ogrenci isleri",
    "ogretim suresi":    "azami ogretim suresi lisans donem yil uzatma ek sure",
}

EXPANSION_PROMPT = """Bir universite ogrencisinin gunluk dilde sordugu soruyu,
universite yonetmeligi metinlerinde daha iyi arama yapabilmek icin
resmi Turkce akademik/hukuki terimlerle zenginlestirilmis bir arama sorgusuna donustur.

Sadece Turkce arama terimi yaz (5-12 kelime). Baska hicbir sey yazma.

Ornekler:
Soru: ustten ders alabilirmiyim
Donusum: ust yariyil ders alma sarti GNO not ortalamasi 3.00 akademik danisман onayi

Soru: sinifi gecemem ne olur
Donusum: basarisiz ogrenci genel not ortalamasi GNO sinif gecme sarti ders tekrari

Soru: dersten cekilebilir miyim
Donusum: ders birakma cekilme kayit silme yariyil akademik takvim

Soru: cift anadal sartlari nelerdir
Donusum: cift anadal programa basvuru sarti GNO not ortalamasi AKTS kredi

Soru: staj zorunlu mu
Donusum: zorunlu staj pratik calisma mezuniyet sarti toplam kredi

Soru: mazeret sinavi nasil alinir
Donusum: mazeret sinavi hakki basvuru belge saglik raporu haklı gerekce yonetim kurulu

Soru: {question}
Donusum:"""


@dataclass
class RAGResult:
    """RAG pipeline'inin tek bir sorguya verdigi yaniti temsil eder."""
    question: str
    answer: str
    sources: list[str]
    model: str
    retrieved_chunks: list = field(default_factory=list)
    latency_ms: float = 0.0
    num_chunks_retrieved: int = 0


class RAGPipeline:
    """
    Firat Mevzuat dijital asistan pipeline'i.

    1. Gemini ile sorguyu genislet (query expansion)
    2. Genisletilmis sorgu ile ChromaDB + BM25 hibrit arama
    3. Dusuk skorlu chunk'lari filtrele
    4. LLM ile kaynakli cevap uret
    """

    def __init__(self, top_k: int = 15, min_score: float = MIN_RELEVANCE_SCORE):
        self.top_k = top_k
        self.min_score = min_score
        self.retriever = MevzuatRetriever()

    def _get_llm_client(self):
        """Mevcut API anahtarına göre OpenAI-uyumlu client döner (Groq veya OpenAI)."""
        if os.getenv("GROQ_API_KEY"):
            try:
                from openai import OpenAI
                return OpenAI(
                    api_key=os.getenv("GROQ_API_KEY"),
                    base_url="https://api.groq.com/openai/v1",
                ), "llama-3.3-70b-versatile"
            except Exception as e:
                logger.warning(f"Groq baslatılamadi: {e}")
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                return OpenAI(api_key=os.getenv("OPENAI_API_KEY")), "gpt-4o-mini"
            except Exception as e:
                logger.warning(f"OpenAI baslatılamadi: {e}")
        return None, None

    def _expand_query(self, question: str) -> str:
        """
        Ogrencinin gunluk dil sorusunu mevzuat terimleriyle zenginlestirir.
        Once statik sozluge bakar, yoksa LLM API kullanir.
        """
        q_lower = question.lower()
        q_normalized = _normalize_tr(q_lower)

        # 1. Once statik sozluge bak (hizli, API gerekmez)
        for keyword, expansion in QUERY_DICT.items():
            if keyword in q_normalized:
                combined = f"{question} {expansion}"
                logger.info(f"Statik expansion: '{question}' -> '{combined[:80]}'")
                return combined

        # 2. Statik esleme yoksa LLM'e sor (Groq veya OpenAI)
        client, model_name = self._get_llm_client()
        if client is None:
            return question

        try:
            prompt = EXPANSION_PROMPT.format(question=question)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=80,
            )
            expanded = response.choices[0].message.content.strip().split("\n")[0].strip()
            if expanded and len(expanded) > 5:
                logger.info(f"Query expansion: '{question}' -> '{expanded}'")
                return f"{question} {expanded}"
        except Exception as e:
            logger.warning(f"Query expansion basarisiz: {e}")

        return question

    def ask(self, question: str) -> RAGResult:
        """
        Ogrencinin sorusuna cevap verir.

        Args:
            question: Dogal dil sorusu (Turkce)

        Returns:
            RAGResult - cevap, kaynaklar ve metrikler
        """
        start = time.time()
        logger.info(f"Soru isleniyor: '{question}'")

        # 1. Query Expansion - sorguyu mevzuat diline genislet
        expanded_query = self._expand_query(question)

        # 2. Hybrid Retrieval (BM25 + Semantic) ile genisletilmis sorgu
        chunks = self.retriever.retrieve(expanded_query, top_k=self.top_k)

        # 3. Alaka duzeyi filtreleme
        relevant_chunks = [c for c in chunks if c.score >= self.min_score]

        if not relevant_chunks:
            logger.warning(f"Hicbir chunk esigi gecemedi. Ham chunk sayisi: {len(chunks)}")

        # 4. Cevap uretimi (orijinal soruya gore)
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
        """Pipeline'in sorguya hazir olup olmadigini kontrol eder."""
        return self.retriever.is_ready()


if __name__ == "__main__":
    pipeline = RAGPipeline()

    if not pipeline.is_ready():
        print("Once indexleme yapin: python scripts/embed_and_index.py")
    else:
        questions = [
            "Ustten ders alabilir miyim?",
            "Cift anadal icin GPA sarti nedir?",
            "Ogrenci kayit dondurabilir mi?",
        ]
        for q in questions:
            result = pipeline.ask(q)
            print(f"\n{'='*60}")
            print(f"Soru: {result.question}")
            print(f"Cevap: {result.answer[:300]}...")
            print(f"Kaynaklar: {', '.join(result.sources)}")
            print(f"Sure: {result.latency_ms}ms | Chunk: {result.num_chunks_retrieved}")
