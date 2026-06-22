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
from backend.generator import generate_answer, generate_answer_stream

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
# ---------------------------------------------------------------------------
# Statik arama genisleme sozlugu
# Her anahtar kelime ogrenci argosundan resmi mevzuat diline esleme yapar.
# Bir soruda BIRDEN FAZLA anahtar kelime eslesebilir — hepsi birlestirilir.
# ---------------------------------------------------------------------------
QUERY_DICT = {
    # === UST YARIYIL / USTTEN DERS ===
    "ustten ders":       "ust yariyil ders alma sarti GNO not ortalamasi 3.00 ust yariyildan ders alabilir",
    "ust yariyil":       "ust yariyil ders alma sarti GNO not ortalamasi 3.00 ust yariyildan ders alabilir",
    "ust siniftan":      "ust yariyil ders alma sarti GNO not ortalamasi onay akademik danisман",

    # === CIFT ANADAL / YANDAL ===
    "cift anadal":       "cift anadal programa basvuru kabul sarti GNO not ortalamasi yuzde yirmi basari sirasi kontenjan",
    "cap":               "cift anadal programa basvuru kabul sarti GNO not ortalamasi yuzde yirmi basari sirasi kontenjan",
    "yandal":            "yandal programa basvuru sarti GNO AKTS kredi onay bolum baskanligi",
    "minör":             "yandal programa basvuru sarti GNO AKTS kredi onay bolum baskanligi",
    "minor":             "yandal programa basvuru sarti GNO AKTS kredi onay bolum baskanligi",

    # === MAZERET SINAVI ===
    "mazeret sinav":     "mazeret sinavi hakki basvuru belge saglik raporu haklı gecerli mazeret yonetim kurulu",
    "mazeret":           "mazeret sinavi hakki basvuru belge saglik raporu haklı gecerli mazeret yonetim kurulu",
    "sinava giremedin":  "mazeret sinavi hakki basvuru belge saglik raporu gecerli gerekce",
    "sinava giremedim":  "mazeret sinavi hakki basvuru belge saglik raporu gecerli gerekce",
    "sinavi kacirdi":    "mazeret sinavi hakki basvuru belge saglik raporu gecerli gerekce",

    # === KAYIT DONDURMA ===
    "kayit dondur":      "kayit dondurma izinli ayrilma ogrencilik hakki donem ask",
    "izinli ayril":      "kayit dondurma izinli ayrilma basvuru ogrencilik hakki",
    "ara ver":           "kayit dondurma izinli ayrilma ogrencilik hakki basvuru",

    # === MEZUNIYET ===
    "mezun olma":        "mezuniyet sarti toplam kredi AKTS staj bitirme projesi not ortalamasi",
    "mezuniyet":         "mezuniyet sarti toplam kredi AKTS staj bitirme projesi not ortalamasi",
    "bitmez mi":         "azami ogretim suresi mezuniyet sarti toplam kredi tamamlama",
    "ne zaman biter":    "azami ogretim suresi mezuniyet sarti toplam kredi AKTS tamamlama",
    "mezun olamadim":    "azami ogretim suresi uzatma ek sure mezuniyet engelleyen eksik ders",

    # === NOT ORTALAMASI ===
    "not ortalama":      "genel not ortalamasi GNO agirlikli ortalama hesaplama",
    "gno":               "genel not ortalamasi GNO agirlikli ortalama hesaplama ders baari",
    "ortalamam dusuk":   "genel not ortalamasi GNO dusuk akademik yetersizlik uyari",
    "ortalama artir":    "genel not ortalamasi GNO yukseltme tekrar ders akademik danismanlik",
    "cc ile gectim":     "baari notu harf notu CC DD basari sarti ders gecme",
    "ff aldim":          "basarisiz ders not FF tekrar sinav ders tekrari GNO dusme",
    "dc aldim":          "basarisiz ders not DC sarti ders tekrari koşullu geçme",

    # === DERS BIRAKMA / CEKILME ===
    "dersten cekil":     "ders birakma cekilme kayit silme yariyil akademik takvim son gun",
    "ders birak":        "ders birakma cekilme kayit silme yariyil akademik takvim son gun",
    "ders sil":          "ders birakma cekilme kayit silme yariyil akademik takvim son gun",
    "cekildim ders":     "ders birakma cekilme kayit silme yariyil akademik takvim son gun",

    # === STAJ ===
    "staj":              "zorunlu staj pratik calisma mezuniyet sarti kredi AKTS suresi",
    "staj yapmak":       "zorunlu staj pratik calisma mezuniyet sarti kredi suresi belge",
    "stajimu":           "zorunlu staj pratik calisma mezuniyet sarti kredi",

    # === DISIPLIN / KOPYA / CEZA ===
    "disiplin":          "disiplin cezasi ogrenci sinav kopya ihlal yonetmelik hukum",
    "kopya cekti":       "sinav kopya ihlal disiplin cezasi uzaklastirma ogrenci ihlali",
    "hile":              "sinav kopya ihlal disiplin cezasi uzaklastirma ogrenci ihlali",
    "ceza":              "disiplin cezasi ogrenci ihlal uzaklastirma yonetmelik hukum ogrenci",
    "ihrac":             "ogrenci ihrac uzaklastirma disiplin cezasi kurumdan cikis",
    "uzaklastirma":      "disiplin cezasi uzaklastirma ogrenci ihrac yonetmelik hukum",

    # === BURS ===
    "burs":              "burs basvuru sarti basari kriteri sosyal yardim kontenjan",
    "burs alabilir":     "burs basvuru sarti basari kriteri sosyal yardim gelir siniri",
    "kredi":             "kredi burs ogrenci kredisi basvuru sarti geri odeme",

    # === YATAY GECIS ===
    "yatay gecis":       "yatay gecis basvuru sarti kontenjan not ortalamasi kabul komisyon",
    "baska okula gecis": "yatay gecis basvuru sarti kontenjan not ortalamasi universiti",
    "transfer":          "yatay gecis basvuru sarti kontenjan not ortalamasi universiti kabul",

    # === DIKEY GECIS ===
    "dikey gecis":       "dikey gecis basvuru DGS sarti sinav puani kontenjan",
    "dgs":               "dikey gecis sinavi DGS basvuru sarti puan kontenjan",
    "onlisanstan":       "dikey gecis basvuru DGS sarti onlisans mezuniyet",

    # === AF ===
    "af":                "ogrenci af kanunu egitim ogretim suresi uzatma ek sure hakki",
    "af cikti mi":       "ogrenci af kanunu egitim ogretim suresi uzatma resmi gazete",

    # === BASARISIZLIK / SINIF TEKRAR ===
    "sinavdan kaldi":    "basarisiz ders tekrar FF DC not ortalama dusum",
    "sinif tekrar":      "sinif tekrar basarisiz ders yuk GNO dusme akademik uyari",
    "butte gecmek":      "sinav baari notu sinif gecme sarti GNO basarisiz",
    "butte kalmak":      "basarisiz ders tekrar FF sinif gecememe akademik yetersizlik",
    "kan":               "sinav not baari esigi harf notu hesaplama GNO",
    "cana gelmek":       "sinav baari notu sinif gecme sarti GNO iyilestirme",

    # === AZAMI SURE / ILISIK KESME ===
    "ust uste":          "azami ogretim suresi ust uste basarisiz donem ilisik kesme kayit silme ogrencilik sona ermesi",
    "kac donem":         "azami ogretim suresi ust uste basarisiz donem ilisik kesme kayit silme",
    "ogrencilik sona":   "azami ogretim suresi ilisik kesme kayit silme ogrencilik sona ermesi",
    "ilisik kesme":      "ilisik kesme kayit silme azami ogretim suresi basarisiz donem",
    "azami sure":        "azami ogretim suresi ust sinir toplam sure donem yil",
    "ogretim suresi":    "azami ogretim suresi lisans donem yil uzatma ek sure",
    "okulu uzatmak":     "azami ogretim suresi uzatma ek sure basvuru yonetim kurulu",

    # === MUAFIYET / INTIBAK ===
    "muafiyet":          "ders muafiyeti intibak yatay gecis bolum baskanligi yonetim kurulu",
    "muaf olma":         "ders muafiyeti intibak yatay gecis bolum baskanligi yonetim kurulu",
    "sayilir mi":        "ders muafiyeti denklik intibak kredi sayilma yonetim kurulu",

    # === NOT DONUSUMU / ERASMUS ===
    "not donusum":       "not donusumu ECTS kredi donusum tablosu erasmus yurt disi denklik",
    "erasmus":           "erasmus yurt disi egitim not donusumu ECTS kredi denklik transkript",
    "yurt disi":         "erasmus yurt disi egitim not donusumu ECTS kredi denklik",
    "exchange":          "erasmus exchange yurt disi egitim not donusumu ECTS kredi denklik",

    # === KAYIT YENILEME ===
    "kayit yenile":      "kayit yenileme donem baslangici akademik takvim borc ders secimi",
    "kayit yaptirma":    "kayit yenileme donem baslangici akademik takvim borc",
    "kayit olmadim":     "kayit yenileme gecikme mazeretli basvuru akademik takvim",

    # === DEVAMSIZLIK ===
    "devamsizlik":       "devamsizlik yoklama oran yuzde otuz ders devam zorunlulugu sarti",
    "yoklama":           "devamsizlik yoklama oran yuzde otuz ders devam zorunlulugu",
    "devama girmedi":    "devamsizlik yoklama oran yuzde otuz sinava girme hakki",
    "devamsiz":          "devamsizlik yoklama oran yuzde otuz sinava girme hakki",

    # === DERS YUKU ===
    "ders yuku":         "ders yuku kredi AKTS maksimum sinir donem basarisizligi",
    "kac ders alabilir": "ders yuku kredi AKTS maksimum sinir donem sarti GNO",
    "ders sayisi":       "ders yuku kredi AKTS maksimum sinir yariyil ders adedi",

    # === BELGELER / TRANSKRIPT ===
    "transkript":        "transkript not belgesi onaylı resmi ogrenci isleri daire baskanligi",
    "ogrenci belgesi":   "ogrenci belgesi talep resmi ogrenci isleri devam belgesi",
    "belge":             "resmi belge tasdik onay ogrenci isleri daire baskanligi",

    # === SINAV TAKVIMI / SONUCLARI ===
    "sinav sonuclari":   "sinav sonuclari ilan itiraz suresi not guncelleme",
    "notu degistir":     "not itiraz suresi sinav kagidi inceleme yonetim kurulu",
    "itiraz":            "sinav not itiraz basvuru suresi kagit inceleme bolum baskanligi",
    "not itiraz":        "sinav not itiraz basvuru suresi sinav kagidi inceleme",

    # === MEZUNIYET SONRASI ===
    "diploma":           "diploma teslimi mezuniyet belgesi ogrenci isleri teslim suresi",
    "mezuniyet belgesi": "diploma teslimi mezuniyet belgesi ogrenci isleri",
}

# ---------------------------------------------------------------------------
# LLM Prompt — statik esleme bulamazsa devreye girer
# ---------------------------------------------------------------------------
EXPANSION_PROMPT = """Sen bir Türk üniversite mevzuatı uzmanısın.
Aşağıdaki öğrenci sorusunu, üniversite yönetmeliği PDF metinlerinde tam metin araması yapmak için
resmi Türkçe hukuki/akademik terimlerle zenginleştirilmiş 6-12 kelimelik bir arama sorgusuna dönüştür.

Kuralllar:
- Yalnızca Türkçe terim yaz
- Resmi yönetmelik dilini kullan ("azami öğretim süresi", "GNO", "AKTS" vb.)
- Öğrencinin kendi kullandığı argoya yer verme
- Başka hiçbir şey yazma, sadece arama terimlerini yaz

Örnekler:
Soru: üstten ders alabilir miyim
Dönüşüm: üst yarıyıl ders alma şartı GNO not ortalaması 3.00 akademik danışman onayı

Soru: sınıfı geçemem ne olur
Dönüşüm: başarısız öğrenci genel not ortalaması GNO sınıf geçme şartı ders tekrarı

Soru: dersten çekilebilir miyim
Dönüşüm: ders bırakma çekilme kayıt silme yarıyıl akademik takvim son gün

Soru: çift anadal şartları nelerdir
Dönüşüm: çift anadal programa başvuru şartı GNO not ortalaması AKTS kredi kontenjan

Soru: staj zorunlu mu
Dönüşüm: zorunlu staj pratik çalışma mezuniyet şartı toplam kredi AKTS

Soru: mazeret sınavı nasıl alınır
Dönüşüm: mazeret sınavı hakkı başvuru belge sağlık raporu haklı gerekçe yönetim kurulu

Soru: disiplin cezası nasıl verilir
Dönüşüm: disiplin cezası öğrenci ihlal uzaklaştırma yönetmelik hüküm soruşturma

Soru: not itirazı nasıl yapılır
Dönüşüm: sınav not itiraz başvuru süresi sınav kâğıdı inceleme bölüm başkanlığı

Soru: {question}
Dönüşüm:"""


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

        Gelistirmeler:
        - Coklu keyword esleme: ilk bulduğunda durmak yerine TUM eslesmeleri toplar
        - Soru tipi tespiti: "ne zaman", "ceza", "itiraz" gibi patternlere gore ek terim
        - LLM fallback: statik sozlukte esleme yoksa Groq/OpenAI'ye gonder
        """
        q_lower = question.lower()
        q_normalized = _normalize_tr(q_lower)

        # 1. Statik sozlukte TUM eslesmeleri topla (ilkinde durma!)
        matched_expansions = []
        matched_keys = []
        for keyword, expansion in QUERY_DICT.items():
            if keyword in q_normalized:
                matched_expansions.append(expansion)
                matched_keys.append(keyword)

        if matched_expansions:
            # Tekrar eden kelimeleri temizleyerek birlestir
            all_terms = set()
            for exp in matched_expansions:
                all_terms.update(exp.split())
            combined_expansion = " ".join(all_terms)
            combined = f"{question} {combined_expansion}"
            logger.info(
                f"Statik expansion ({len(matched_keys)} esleme: {matched_keys}): "
                f"'{question}' -> '{combined[:100]}'"
            )
            return combined

        # 2. Soru tipi tespiti — ek bağlam terimi ekle
        question_type_hints = ""
        if any(p in q_normalized for p in ["ne zaman", "hangi tarih", "kac gun", "suresi"]):
            question_type_hints = "akademik takvim sure tarih gun sinir"
        elif any(p in q_normalized for p in ["ceza", "suclama", "ihlal", "sorusturma"]):
            question_type_hints = "disiplin cezasi ogrenci ihlal uzaklastirma yonetmelik hukum"
        elif any(p in q_normalized for p in ["itiraz", "sikayyet", "sikayet"]):
            question_type_hints = "itiraz basvuru sure bolum baskanligi yonetim kurulu"
        elif any(p in q_normalized for p in ["sarti", "kriter", "gerekli", "nasil", "ne lazim"]):
            question_type_hints = "basvuru sarti kriter gereksinim yonetmelik hukum"

        # 3. Statik esleme yoksa LLM'e sor (Groq veya OpenAI)
        client, model_name = self._get_llm_client()
        if client is None:
            # LLM de yoksa soru tipi ipucuyla geri don
            base = question
            if question_type_hints:
                base = f"{question} {question_type_hints}"
                logger.info(f"Soru tipi ipucu eklendi: '{question}' -> '{base[:80]}'")
            return base

        try:
            prompt = EXPANSION_PROMPT.format(question=question)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100,
            )
            expanded = response.choices[0].message.content.strip().split("\n")[0].strip()
            if expanded and len(expanded) > 5:
                # Soru tipi ipucunu da ekle
                full = f"{question} {expanded}"
                if question_type_hints:
                    full = f"{full} {question_type_hints}"
                logger.info(f"LLM expansion: '{question}' -> '{full[:100]}'")
                return full
        except Exception as e:
            logger.warning(f"Query expansion basarisiz: {e}")

        # Son care: ham soruya soru tipi ipucunu birlestir
        if question_type_hints:
            return f"{question} {question_type_hints}"
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

    def ask_stream(self, question: str, history: list = None):
        """
        Ogrencinin sorusuna kelime kelime (streaming) cevap verir.
        Son chunk olarak kaynaklari ve metrikleri dondurur.
        """
        import json
        start = time.time()
        logger.info(f"Soru isleniyor (Stream): '{question}'")

        history = history or []
        search_query = question
        if history:
            last_user_msgs = [msg["content"] for msg in history if msg["role"] == "user"]
            if last_user_msgs:
                search_query = last_user_msgs[-1] + " " + question

        expanded_query = self._expand_query(search_query)
        chunks = self.retriever.retrieve(expanded_query, top_k=self.top_k)
        relevant_chunks = [c for c in chunks if c.score >= self.min_score]

        if not relevant_chunks:
            logger.warning(f"Hicbir chunk esigi gecemedi. Ham chunk sayisi: {len(chunks)}")

        model_out = []
        for text_chunk in generate_answer_stream(question, relevant_chunks, model_out, history=history):
            # SSE formati icin metin chunk'i:
            yield f"data: {json.dumps({'type': 'content', 'text': text_chunk})}\n\n"
        
        latency = round((time.time() - start) * 1000, 1)
        
        sources_dict = {}
        for c in relevant_chunks:
            if c.citation() not in sources_dict:
                sources_dict[c.citation()] = c.text
                
        sources = [{"citation": k, "text": v} for k, v in sources_dict.items()]

        model_name = model_out[0] if model_out else "unknown"
        
        meta = {
            'type': 'meta',
            'sources': sources,
            'latency_ms': latency,
            'num_chunks': len(relevant_chunks),
            'model': model_name
        }
        yield f"data: {json.dumps(meta)}\n\n"
        yield "data: [DONE]\n\n"

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
