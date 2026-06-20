"""
Hangi source_file hangi yonetmeligi iceriyor bul.
Benchmark dataset icin dogru source_file eslesmelerini gosterir.
"""
import sys, os, json
sys.path.insert(0, ".")
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ef = SentenceTransformerEmbeddingFunction(model_name="dbmdz/bert-base-turkish-cased", device="cpu")
client = chromadb.PersistentClient(path="./chroma_db")
col = client.get_collection(name="firat_mevzuat", embedding_function=ef)

# Benchmark sorularini tanimli sorgularla ara
queries = {
    "Mazeret sinavi": ("mazeret sinav hakki basvuru saglik raporu", ["15", "16"]),
    "Cift anadal GPA": ("cift anadal basvuru GPA 3.00 not ortalama", ["5"]),
    "Ust uste basarisiz": ("azami ogretim suresi ust uste basarisiz ilisik kesme", ["32"]),
    "Kayit dondurma": ("kayit dondurma izinli ayrilma sure basvuru", ["10", "11"]),
    "Disiplin uzaklastirma": ("disiplin cezasi uzaklastirma yariyil ogrenci", ["8","9","10"]),
    "Tek ders sinavi": ("tek ders sinavi mezuniyet sart", ["28"]),
    "Yatay gecis": ("yatay gecis basvuru AGNO kontenjam sart", ["4","5","6"]),
    "Staj mezuniyet": ("staj zorunlulugu mezuniyet sart", ["22","23"]),
    "Ders muafiyeti": ("ders muafiyeti bolum baskanligi yonetim kurulu", ["7"]),
    "Erasmus not donusum": ("erasmus not donusum ECTS transkript", ["18","19"]),
}

print("=== BENCHMARK ESLESME ANALIZI ===\n")
for qname, (query, expected_arts) in queries.items():
    res = col.query(query_texts=[query], n_results=10, include=["metadatas","distances"])
    print(f"[{qname}]  beklenen_madde={expected_arts}")
    for m, d in zip(res["metadatas"][0], res["distances"][0]):
        hit = ">> MATCH" if m["article_no"] in expected_arts else "       "
        print(f"  {hit} madde={m['article_no']:>4} | src={m['source_file'][:20]:<20} | reg={m['regulation_name'][:35]:<35} | d={d:.3f}")
    print()
