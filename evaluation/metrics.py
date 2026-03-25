"""
metrics.py
----------
Retrieval ve cevap kalitesini ölçen metrik hesaplayıcısı.

Hesaplanan metrikler:
    Retrieval: Precision@K, Recall@K, MRR (Mean Reciprocal Rank)
    Answer:    ROUGE-L, BLEU-4
"""

import logging
from collections import defaultdict

import numpy as np
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

logger = logging.getLogger(__name__)


# ── Retrieval Metrikleri ───────────────────────────────────────────────────────

def precision_at_k(retrieved_articles: list[str], relevant_articles: list[str], k: int) -> float:
    """
    Precision@K: İlk K sonuçta kaçı gerçekten doğru?
    retrieved_articles: sistem tarafından döndürülen madde no listesi (sıralı)
    relevant_articles:  doğru cevabın madde no'ları (ground truth)
    """
    top_k = retrieved_articles[:k]
    hits = sum(1 for a in top_k if a in relevant_articles)
    return hits / k if k > 0 else 0.0


def recall_at_k(retrieved_articles: list[str], relevant_articles: list[str], k: int) -> float:
    """
    Recall@K: Doğru maddelerin kaçını ilk K'da bulduk?
    """
    top_k = retrieved_articles[:k]
    hits = sum(1 for a in relevant_articles if a in top_k)
    return hits / len(relevant_articles) if relevant_articles else 0.0


def reciprocal_rank(retrieved_articles: list[str], relevant_articles: list[str]) -> float:
    """
    Reciprocal Rank: İlk doğru sonuç kaçıncı sırada?
    MRR için bu değerlerin ortalaması alınır.
    """
    for i, article in enumerate(retrieved_articles, 1):
        if article in relevant_articles:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(results: list[tuple]) -> float:
    """
    MRR: Tüm sorgular için reciprocal rank ortalaması.
    results: [(retrieved_list, relevant_list), ...]
    """
    rr_scores = [reciprocal_rank(ret, rel) for ret, rel in results]
    return np.mean(rr_scores)


# ── Cevap Kalite Metrikleri ────────────────────────────────────────────────────

def rouge_l_score(hypothesis: str, reference: str) -> float:
    """ROUGE-L F1 skoru döner (0-1 arası)."""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    scores = scorer.score(reference, hypothesis)
    return round(scores["rougeL"].fmeasure, 4)


def bleu_4_score(hypothesis: str, reference: str) -> float:
    """BLEU-4 skoru döner (0-1 arası)."""
    hypothesis_tokens = hypothesis.split()
    reference_tokens = [reference.split()]
    smoothing = SmoothingFunction().method1
    try:
        score = sentence_bleu(reference_tokens, hypothesis_tokens, smoothing_function=smoothing)
        return round(score, 4)
    except Exception:
        return 0.0


# ── Toplu Değerlendirme ────────────────────────────────────────────────────────

def evaluate_batch(test_cases: list[dict]) -> dict:
    """
    Bir test seti için tüm metrikleri hesaplar.

    test_cases formatı:
    [
        {
            "question": "...",
            "expected_articles": ["5", "12"],
            "retrieved_articles": ["5", "3", "12", "8", "1"],
            "generated_answer": "...",
            "reference_answer": "..."
        },
        ...
    ]

    Returns:
        {
            "precision@1": 0.72,
            "precision@3": 0.61,
            "recall@5": 0.84,
            "mrr": 0.79,
            "rouge_l": 0.45,
            "bleu_4": 0.31
        }
    """
    p1_list, p3_list, r5_list, rr_list = [], [], [], []
    rouge_list, bleu_list = [], []

    for case in test_cases:
        retrieved = case.get("retrieved_articles", [])
        expected = case.get("expected_articles", [])
        generated = case.get("generated_answer", "")
        reference = case.get("reference_answer", "")

        p1_list.append(precision_at_k(retrieved, expected, 1))
        p3_list.append(precision_at_k(retrieved, expected, 3))
        r5_list.append(recall_at_k(retrieved, expected, 5))
        rr_list.append(reciprocal_rank(retrieved, expected))

        if generated and reference:
            rouge_list.append(rouge_l_score(generated, reference))
            bleu_list.append(bleu_4_score(generated, reference))

    results = {
        "precision@1": round(np.mean(p1_list), 4),
        "precision@3": round(np.mean(p3_list), 4),
        "recall@5": round(np.mean(r5_list), 4),
        "mrr": round(np.mean(rr_list), 4),
    }
    if rouge_list:
        results["rouge_l"] = round(np.mean(rouge_list), 4)
        results["bleu_4"] = round(np.mean(bleu_list), 4)

    return results
