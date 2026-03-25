"""
chunker.py
----------
Ayrıştırılmış maddeleri embedding için uygun boyutlarda chunk'lara böler.

Strateji:
- Kısa maddeler (< 512 token): aynen kullan, bir chunk
- Uzun maddeler (>= 512 token): 512 token pencere, 64 token örtüşme
- Her chunk metadata içerir: kaynak, madde no, yönetmelik adı
"""

import logging
from typing import Generator

logger = logging.getLogger(__name__)

MAX_TOKENS = 512       # BERTurk max token sayısı
OVERLAP_TOKENS = 64    # Bağlamı korumak için örtüşme
AVG_CHARS_PER_TOKEN = 4  # Türkçe için yaklaşık değer


def _estimate_tokens(text: str) -> int:
    """Karakter sayısından yaklaşık token tahmini."""
    return len(text) // AVG_CHARS_PER_TOKEN


def _split_long_text(
    text: str,
    max_chars: int,
    overlap_chars: int
) -> Generator[str, None, None]:
    """Uzun metni örtüşmeli pencerelerle böler."""
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]

        # Cümle sınırında kes (nokta veya satır sonu)
        if end < len(text):
            last_break = max(
                chunk.rfind(". "),
                chunk.rfind("\n"),
            )
            if last_break > max_chars // 2:
                chunk = chunk[:last_break + 1]
                end = start + last_break + 1

        yield chunk.strip()
        start = end - overlap_chars  # örtüşme
        if start >= len(text) - overlap_chars:
            break


def chunk_article(article: dict, chunk_index_start: int = 0) -> list[dict]:
    """
    Tek bir maddeyi chunk'lara böler.

    Args:
        article: pdf_parser.py çıktısındaki madde dict'i
        chunk_index_start: chunk ID sayacı

    Returns:
        Chunk dict listesi
    """
    text = article["text"]
    max_chars = MAX_TOKENS * AVG_CHARS_PER_TOKEN
    overlap_chars = OVERLAP_TOKENS * AVG_CHARS_PER_TOKEN
    chunks = []

    if _estimate_tokens(text) <= MAX_TOKENS:
        # Kısa madde — tek chunk
        chunks.append({
            "chunk_id": chunk_index_start,
            "text": text,
            "regulation_name": article["regulation_name"],
            "article_no": article["article_no"],
            "article_title": article.get("article_title", ""),
            "source_file": article["source_file"],
            "chunk_type": "full_article",
        })
    else:
        # Uzun madde — örtüşmeli pencereler
        for i, sub_text in enumerate(_split_long_text(text, max_chars, overlap_chars)):
            chunks.append({
                "chunk_id": chunk_index_start + i,
                "text": sub_text,
                "regulation_name": article["regulation_name"],
                "article_no": article["article_no"],
                "article_title": article.get("article_title", ""),
                "source_file": article["source_file"],
                "chunk_type": f"split_{i + 1}",
            })

    return chunks


def chunk_all_articles(articles: list[dict]) -> list[dict]:
    """
    Tüm madde listesini chunk'lara dönüştürür.

    Args:
        articles: parse_all_pdfs() çıktısı

    Returns:
        Tüm chunk'ların listesi (metadata dahil)
    """
    all_chunks = []
    counter = 0

    for article in articles:
        article_chunks = chunk_article(article, chunk_index_start=counter)
        all_chunks.extend(article_chunks)
        counter += len(article_chunks)

    logger.info(
        f"{len(articles)} madde → {len(all_chunks)} chunk "
        f"(ort. {len(all_chunks) / max(len(articles), 1):.1f} chunk/madde)"
    )
    return all_chunks


if __name__ == "__main__":
    # Test — pdf_parser.py ile birlikte çalıştırın
    import sys
    import json
    sys.path.insert(0, ".")
    from scripts.pdf_parser import parse_all_pdfs

    articles = parse_all_pdfs("data/raw")
    if articles:
        chunks = chunk_all_articles(articles)
        print(f"\n✅ {len(chunks)} chunk oluşturuldu.")
        print("\nÖrnek chunk:")
        print(json.dumps(chunks[0], ensure_ascii=False, indent=2))
    else:
        print("⚠️  Önce data/raw/ klasörüne PDF ekleyin.")
