"""
ChromaDB'deki benzersiz regulation_name değerlerini listeler.
Benchmark dataset'i için ground truth regulation adlarını tespit etmek amacıyla kullanılır.
"""
import sys, os
sys.path.insert(0, ".")
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ef = SentenceTransformerEmbeddingFunction(model_name="dbmdz/bert-base-turkish-cased", device="cpu")
client = chromadb.PersistentClient(path="./chroma_db")
col = client.get_collection(name="firat_mevzuat", embedding_function=ef)

# regulation_name'e göre gruplama için tüm metadata'yı çek
# ChromaDB get() ile sayfalandırarak al
all_meta = col.get(include=["metadatas"], limit=4000)

reg_names = {}
for m in all_meta["metadatas"]:
    rname = m.get("regulation_name", "")
    src = m.get("source_file", "")
    key = src
    if key not in reg_names:
        reg_names[key] = rname

# Benzersiz regulation_name listesi
unique_regs = sorted(set(reg_names.values()))
print(f"Toplam {len(unique_regs)} benzersiz yonetmelik:\n")
for r in unique_regs:
    print(f"  {r}")

# Benchmark sorularıyla alakalı olanları bul
keywords = ["lisans", "egitim", "sinav", "cift", "anadal", "disiplin", "yatay"]
print("\n--- Alakali olabilecekler ---")
for r in unique_regs:
    r_lower = r.lower()
    if any(k in r_lower for k in keywords):
        print(f"  >> {r}")
