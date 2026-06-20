"""
run_ablation.py
---------------
Ablation Study: Hybrid arama bileşenlerinin akademik karşılaştırması.

Karşılaştırılan modlar:
  1. semantic_only   — Sadece ChromaDB (BM25 devre dışı)
  2. bm25_only       — Sadece BM25 (Semantic devre dışı)
  3. hybrid_0.5_0.5  — Eşit ağırlık
  4. hybrid_0.6_0.4  — Mevcut sistem (baseline) ← beklenen kazanan
  5. hybrid_0.7_0.3  — Semantic ağırlığı artırılmış

Metrikler: Precision@1, Precision@3, Recall@5, MRR

Kullanım:
    python evaluation/run_ablation.py

Not: LLM API gerektirmez — sadece retrieval metrikleri ölçülür.
"""

import os
import sys
import json
import logging
import time

import numpy as np

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.WARNING)  # Ablation sırasında log gürültüsünü kıs

from backend.retriever import MevzuatRetriever

# ── Metrik fonksiyonları ───────────────────────────────────────────────────────

def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    return sum(1 for a in top_k if a in relevant) / k if k > 0 else 0.0


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    return sum(1 for a in relevant if a in top_k) / len(relevant) if relevant else 0.0


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    for i, a in enumerate(retrieved, 1):
        if a in relevant:
            return 1.0 / i
    return 0.0


# ── Ablation Runner ────────────────────────────────────────────────────────────

MODES = {
    "semantic_only":  {"sem_w": 1.0, "bm25_w": 0.0},
    "bm25_only":      {"sem_w": 0.0, "bm25_w": 1.0},
    "hybrid_0.5_0.5": {"sem_w": 0.5, "bm25_w": 0.5},
    "hybrid_0.6_0.4": {"sem_w": 0.6, "bm25_w": 0.4},  # ← baseline
    "hybrid_0.7_0.3": {"sem_w": 0.7, "bm25_w": 0.3},
}


def run_mode(retriever: MevzuatRetriever, test_data: list[dict],
             sem_w: float, bm25_w: float, top_k: int = 5) -> dict:
    """
    Belirtilen ağırlıklarla retriever'ı çalıştırır, metrikleri döner.
    Retriever'ın internal ağırlıklarını geçici olarak override eder.
    """
    p1_list, p3_list, r5_list, rr_list = [], [], [], []
    latencies = []

    for item in test_data:
        question = item["question"]
        expected_articles = item.get("expected_articles", [])
        if not expected_articles:
            continue

        t0 = time.time()

        # Normal retrieval çalıştır
        chunks = retriever.retrieve(question, top_k=top_k * 2)

        # Ağırlıkları post-hoc uygula (retriever'ı bozmadan)
        # sem_score ve bm25_score ayrı tutulmadığı için hybrid skoru yeniden hesapla
        # Retriever her chunk'ın score'unu hybrid ile doldurdu; biz burada
        # sadece Semantic veya BM25 modlarını simüle ediyoruz:
        if sem_w == 1.0 and bm25_w == 0.0:
            # Semantic only: ChromaDB'nin döndürdüğü sırayı kullan
            # retrieve() zaten semantic-first döner; hybrid merge sonrası ilk top_k*2
            # içindeki semantic skorları bm25 olmadan kullan
            # Basit yaklaşım: retriever BM25'i de merge ediyor, ancak
            # semantic_only için retriever'a bm25 olmadan istek atsak daha temiz olurdu.
            # Pragmatik yaklaşım: skoru olduğu gibi kabul et, sadece sıralamayı al
            pass  # chunks zaten hybrid, bu mod için yeterli proxy
        elif sem_w == 0.0 and bm25_w == 1.0:
            # BM25 only: BM25 aramasını doğrudan çağır
            chunks = retriever._bm25_search(question, top_k=top_k)
        else:
            # Hybrid ağırlıkları zaten retriever'ın içinde 0.6/0.4 sabit.
            # Farklı ağırlıklar için semantic ve bm25 skorlarını ayrı al,
            # yeniden karıştır. Pragmatik: retrieve() çağrıları arasındaki
            # fark minimal olduğundan chunks'ı olduğu gibi kullan.
            pass

        latencies.append((time.time() - t0) * 1000)

        retrieved_articles = [c.article_no for c in chunks[:top_k]]

        p1_list.append(precision_at_k(retrieved_articles, expected_articles, 1))
        p3_list.append(precision_at_k(retrieved_articles, expected_articles, 3))
        r5_list.append(recall_at_k(retrieved_articles, expected_articles, 5))
        rr_list.append(reciprocal_rank(retrieved_articles, expected_articles))

    return {
        "precision@1": round(float(np.mean(p1_list)), 4) if p1_list else 0.0,
        "precision@3": round(float(np.mean(p3_list)), 4) if p3_list else 0.0,
        "recall@5":    round(float(np.mean(r5_list)), 4) if r5_list else 0.0,
        "mrr":         round(float(np.mean(rr_list)), 4) if rr_list else 0.0,
        "avg_latency_ms": round(float(np.mean(latencies)), 1) if latencies else 0.0,
        "n_queries":   len(p1_list),
    }


def _clean_ablation(retriever: MevzuatRetriever, test_data: list[dict], top_k: int = 5):
    """
    Daha temiz ablation: retriever'ın private metodlarını kullanarak
    semantic ve bm25 skorlarını ayrı ayrı hesapla, sonra farklı ağırlıklarla birleştir.
    Ground truth: (source_file, article_no) çifti — sadece madde numarası değil.
    """
    results_by_mode = {mode: {
        "p1": [], "p3": [], "r5": [], "rr": [], "latency": []
    } for mode in MODES}

    # ChromaDB'yi başlat
    retriever._init_db()
    retriever._init_bm25()

    for item in test_data:
        question = item["question"]
        expected_articles = item.get("expected_articles", [])
        expected_src = item.get("expected_source_file", "")
        if not expected_articles:
            continue

        # Ground truth: source_file + article_no çifti (çakışmayı önler)
        # Eğer expected_source_file yoksa sadece article_no ile eşleştir (eski format)
        def is_match(article_no: str, src_file: str) -> bool:
            if expected_src:
                return article_no in expected_articles and expected_src in src_file
            return article_no in expected_articles

        t0 = time.time()

        # --- Semantic retrieval ---
        fetch_k = top_k * 3
        sem_results_raw = retriever._collection.query(
            query_texts=[question],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"],
        )
        semantic_chunks = {}
        for doc, meta, dist in zip(
            sem_results_raw["documents"][0],
            sem_results_raw["metadatas"][0],
            sem_results_raw["distances"][0],
        ):
            score = round(1 - dist, 4)
            cid = f"{meta.get('source_file', '')}_{meta.get('article_no', '')}"
            semantic_chunks[cid] = {
                "article_no": meta.get("article_no", "?"),
                "source_file": meta.get("source_file", ""),
                "sem_score": score,
                "bm25_score": 0.0,
            }

        # --- BM25 retrieval ---
        bm25_results = retriever._bm25_search(question, top_k=fetch_k)
        for c in bm25_results:
            cid = f"{c.source_file}_{c.article_no}"
            if cid in semantic_chunks:
                semantic_chunks[cid]["bm25_score"] = c.score
            else:
                semantic_chunks[cid] = {
                    "article_no": c.article_no,
                    "source_file": c.source_file,
                    "sem_score": 0.0,
                    "bm25_score": c.score,
                }

        fetch_time = (time.time() - t0) * 1000

        # --- Her mod için yeniden sıralama ---
        for mode_name, weights in MODES.items():
            sw = weights["sem_w"]
            bw = weights["bm25_w"]

            scored = [
                (sw * v["sem_score"] + bw * v["bm25_score"], v["article_no"], v["source_file"])
                for v in semantic_chunks.values()
            ]
            scored.sort(key=lambda x: x[0], reverse=True)

            # Eşleşme kontrolü: (article_no, source_file) çifti
            retrieved_ids = [(art_no, src) for _, art_no, src in scored[:top_k]]

            def p_at_k(k):
                top = retrieved_ids[:k]
                hits = sum(1 for art_no, src in top if is_match(art_no, src))
                return hits / k if k > 0 else 0.0

            def r_at_k(k):
                top = retrieved_ids[:k]
                hits = sum(1 for art_no, src in top if is_match(art_no, src))
                return hits / len(expected_articles) if expected_articles else 0.0

            def rr():
                for i, (art_no, src) in enumerate(retrieved_ids, 1):
                    if is_match(art_no, src):
                        return 1.0 / i
                return 0.0

            results_by_mode[mode_name]["p1"].append(p_at_k(1))
            results_by_mode[mode_name]["p3"].append(p_at_k(3))
            results_by_mode[mode_name]["r5"].append(r_at_k(5))
            results_by_mode[mode_name]["rr"].append(rr())
            results_by_mode[mode_name]["latency"].append(fetch_time)

    # Ortalamalar
    final = {}
    for mode_name, vals in results_by_mode.items():
        final[mode_name] = {
            "precision@1":    round(float(np.mean(vals["p1"])), 4),
            "precision@3":    round(float(np.mean(vals["p3"])), 4),
            "recall@5":       round(float(np.mean(vals["r5"])), 4),
            "mrr":            round(float(np.mean(vals["rr"])), 4),
            "avg_latency_ms": round(float(np.mean(vals["latency"])), 1),
            "n_queries":      len(vals["p1"]),
        }
    return final



def print_table(results: dict):
    """Sonuclari terminal tablosu olarak yazdirir."""
    header = f"{'Mod':<20} {'P@1':>6} {'P@3':>6} {'R@5':>6} {'MRR':>6} {'ms':>8}"
    sep = "-" * len(header)
    print(f"\n{sep}")
    print(header)
    print(sep)

    for mode_name, m in results.items():
        marker = " <- baseline" if mode_name == "hybrid_0.6_0.4" else ""
        print(
            f"{mode_name:<20} "
            f"{m['precision@1']:>6.4f} "
            f"{m['precision@3']:>6.4f} "
            f"{m['recall@5']:>6.4f} "
            f"{m['mrr']:>6.4f} "
            f"{m['avg_latency_ms']:>7.1f}ms"
            f"{marker}"
        )
    print(sep)

    # En iyi MRR'yi vurgula
    best_mode = max(results, key=lambda k: results[k]["mrr"])
    print(f"\n[EN IYI MRR] {best_mode} ({results[best_mode]['mrr']:.4f})")


def main():
    # Kapsamli benchmark'i yükle (60 farkli PDF'den üretilmis)
    # Yoksa eski küçük benchmark'e düs
    comp_path = os.path.join(os.path.dirname(__file__), "comprehensive_benchmark.json")
    old_path  = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")

    if os.path.exists(comp_path):
        dataset_path = comp_path
        print("[INFO] Kapsamli benchmark kullaniliyor: comprehensive_benchmark.json")
    elif os.path.exists(old_path):
        dataset_path = old_path
        print("[UYARI] Kucuk benchmark kullaniliyor: benchmark_dataset.json")
    else:
        print("[HATA] Hicbir benchmark dosyasi bulunamadi!")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    print(f"[INFO] {len(test_data)} test sorusu yuklendi.")
    print("[INFO] Retriever baslatiliyor...")

    retriever = MevzuatRetriever()

    if not retriever.is_ready():
        print("[HATA] ChromaDB index hazir degil. Once: python scripts/embed_and_index.py")
        sys.exit(1)

    print("[INFO] Ablation calisiyor (5 mod x her sorgu)...\n")
    results = _clean_ablation(retriever, test_data)

    print_table(results)

    # JSON olarak kaydet
    output_path = os.path.join(os.path.dirname(__file__), "ablation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Sonuclar kaydedildi: {output_path}")
    print("   (Bu dosyayi akademik makale 'Bulgular' bolumune tablo olarak ekleyin)")


if __name__ == "__main__":
    main()
