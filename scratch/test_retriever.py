from backend.retriever import MevzuatRetriever

retriever = MevzuatRetriever()
query = "Disiplin cezası ne zaman kaldırılır?"
print(f"Query: {query}\n")

print("--- BM25 Results ---")
bm25_res = retriever._bm25_search(query, 5)
for r in bm25_res:
    print(f"Score: {r.score:.3f} | File: {r.source_file} | Text: {r.text[:50]}...")

print("\n--- Semantic Results ---")
retriever._init_db()
sem_res = retriever._collection.query(query_texts=[query], n_results=5)
for doc, meta, dist in zip(sem_res["documents"][0], sem_res["metadatas"][0], sem_res["distances"][0]):
    print(f"Score: {1-dist:.3f} | File: {meta['source_file']} | Text: {doc[:50]}...")
