import sys
import os
sys.path.insert(0, ".")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ef = SentenceTransformerEmbeddingFunction(model_name="dbmdz/bert-base-turkish-cased", device="cpu")
client = chromadb.PersistentClient(path="./chroma_db")
col = client.get_collection(name="firat_mevzuat", embedding_function=ef)

print(f"Toplam chunk: {col.count()}")

# Mazeret sinavi sorusu
res = col.query(
    query_texts=["Mazeret sinavi hakkından kimler yararlanabilir?"],
    n_results=7,
    include=["metadatas", "distances"]
)
print("\n=== Mazeret sinavi sorusu ===")
print(f"  expected_articles: ['15', '16']")
for m, d in zip(res["metadatas"][0], res["distances"][0]):
    hit = "MATCH" if m["article_no"] in ["15", "16"] else "     "
    print(f"  {hit} article_no={m['article_no']:>6} | {m['regulation_name'][:45]:<45} | dist={d:.4f}")

# Cift anadal
res2 = col.query(
    query_texts=["Cift anadal programina basvurmak icin gereken asgari GPA nedir?"],
    n_results=7,
    include=["metadatas", "distances"]
)
print("\n=== Cift anadal GPA sorusu ===")
print(f"  expected_articles: ['5']")
for m, d in zip(res2["metadatas"][0], res2["distances"][0]):
    hit = "MATCH" if m["article_no"] in ["5"] else "     "
    print(f"  {hit} article_no={m['article_no']:>6} | {m['regulation_name'][:45]:<45} | dist={d:.4f}")

# Kayit dondurma
res3 = col.query(
    query_texts=["Kayit dondurma basvuru suresi ne zaman biter?"],
    n_results=7,
    include=["metadatas", "distances"]
)
print("\n=== Kayit dondurma sorusu ===")
print(f"  expected_articles: ['10', '11']")
for m, d in zip(res3["metadatas"][0], res3["distances"][0]):
    hit = "MATCH" if m["article_no"] in ["10", "11"] else "     "
    print(f"  {hit} article_no={m['article_no']:>6} | {m['regulation_name'][:45]:<45} | dist={d:.4f}")
