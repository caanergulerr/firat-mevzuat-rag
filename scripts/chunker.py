"""
chunker.py
----------
Ayrıştırılmış maddeleri embedding için uygun boyutlarda chunk'lara böler.

Strateji:
- Kısa maddeler (<= MAX_TOKENS token): aynen kullan, tek chunk
- Uzun maddeler (> MAX_TOKENS token): MAX_TOKENS pencere, OVERLAP_TOKENS örtüşme
- Her chunk metadata içerir: kaynak, madde no, yönetmelik adı

Token sayımı: dbmdz/bert-base-turkish-cased AutoTokenizer ile yapılır.
Karakter tahmini kullanılmaz — akademik metodoloji gereği gerçek tokenizasyon.
"""

import logging
from typing import Generator

logger = logging.getLogger(__name__)

MAX_TOKENS = 450       # BERTurk max 512; [CLS]+[SEP] için 2, ChromaDB payı için ~60 ayrılır
OVERLAP_TOKENS = 64    # Bağlamı korumak için örtüşme (token cinsinden)

# ── Tokenizer Singleton ────────────────────────────────────────────────────────
_tokenizer = None

def _get_tokenizer():
    """
    BERTurk tokenizer'ını singleton olarak döner.
    İlk çağrıda yükler, sonraki çağrılarda cache'den döner.
    """
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer
        logger.info("BERTurk tokenizer yükleniyor: dbmdz/bert-base-turkish-cased")
        _tokenizer = AutoTokenizer.from_pretrained(
            "dbmdz/bert-base-turkish-cased",
            use_fast=True,   # Rust tabanlı hızlı tokenizer
        )
        logger.info("Tokenizer hazır.")
    return _tokenizer


def _count_tokens(text: str) -> int:
    """Metindeki gerçek BERTurk token sayısını döner (özel tokenlar hariç)."""
    tokenizer = _get_tokenizer()
    # add_special_tokens=False → [CLS] ve [SEP]'i saymaz
    return len(tokenizer.encode(text, add_special_tokens=False))


def _split_by_tokens(text: str) -> Generator[str, None, None]:
    """
    Metni MAX_TOKENS token'lık örtüşmeli pencerelerle böler.

    Yaklaşım:
    1. Metni cümlelere/satırlara göre önce böl (kaba bölüm)
    2. Her bölümü biriktir; token limiti aşılmadan önce chunk'a ekle
    3. Limit aşıldığında mevcut birikimi yield et, OVERLAP_TOKENS kadar geri al
    """
    tokenizer = _get_tokenizer()

    # Cümle/satır sınırlarında böl (nokta + boşluk veya satır sonu)
    import re
    sentences = re.split(r'(?<=\. )|(?<=\n)', text)
    sentences = [s for s in sentences if s.strip()]

    current_tokens: list[int] = []
    current_texts: list[str] = []

    for sentence in sentences:
        sent_ids = tokenizer.encode(sentence, add_special_tokens=False)

        if len(current_tokens) + len(sent_ids) > MAX_TOKENS:
            # Mevcut birikimleri ver
            if current_tokens:
                chunk_text = tokenizer.decode(current_tokens, skip_special_tokens=True)
                yield chunk_text.strip()

                # OVERLAP: son OVERLAP_TOKENS token'ı bir sonraki chunk'a taşı
                overlap_ids = current_tokens[-OVERLAP_TOKENS:]
                current_tokens = overlap_ids
                current_texts = [tokenizer.decode(overlap_ids, skip_special_tokens=True)]

            # Tek cümle bile limiti aşıyorsa zorla böl
            if len(sent_ids) > MAX_TOKENS:
                for i in range(0, len(sent_ids), MAX_TOKENS - OVERLAP_TOKENS):
                    window = sent_ids[i: i + MAX_TOKENS]
                    yield tokenizer.decode(window, skip_special_tokens=True).strip()
                current_tokens = []
                current_texts = []
                continue

        current_tokens.extend(sent_ids)
        current_texts.append(sentence)

    # Kalan metin
    if current_tokens:
        chunk_text = tokenizer.decode(current_tokens, skip_special_tokens=True)
        if chunk_text.strip():
            yield chunk_text.strip()


def chunk_article(article: dict, chunk_index_start: int = 0) -> list[dict]:
    """
    Tek bir maddeyi chunk'lara böler.

    Args:
        article: pdf_parser.py çıktısındaki madde dict'i
        chunk_index_start: chunk ID sayacı

    Returns:
        Chunk dict listesi (her birinde token_count metadatası var)
    """
    text = article["text"]
    chunks = []

    if _count_tokens(text) <= MAX_TOKENS:
        # Kısa madde — tek chunk, aynen kullan
        chunks.append({
            "chunk_id": chunk_index_start,
            "text": text,
            "regulation_name": article["regulation_name"],
            "article_no": article["article_no"],
            "article_title": article.get("article_title", ""),
            "source_file": article["source_file"],
            "chunk_type": "full_article",
            "token_count": _count_tokens(text),
        })
    else:
        # Uzun madde — gerçek token tabanlı örtüşmeli pencereler
        for i, sub_text in enumerate(_split_by_tokens(text)):
            chunks.append({
                "chunk_id": chunk_index_start + i,
                "text": sub_text,
                "regulation_name": article["regulation_name"],
                "article_no": article["article_no"],
                "article_title": article.get("article_title", ""),
                "source_file": article["source_file"],
                "chunk_type": f"split_{i + 1}",
                "token_count": _count_tokens(sub_text),
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
    # Test + token dağılımı raporu
    import sys
    import json
    import statistics
    sys.path.insert(0, ".")
    from scripts.pdf_parser import parse_all_pdfs

    articles = parse_all_pdfs("data/raw")
    if articles:
        chunks = chunk_all_articles(articles)
        token_counts = [c["token_count"] for c in chunks]

        print(f"\n✅ {len(chunks)} chunk oluşturuldu.")
        print("\n📊 Token Dağılımı (Akademik Rapor):")
        print(f"   Min  : {min(token_counts)} token")
        print(f"   Max  : {max(token_counts)} token")
        print(f"   Ort. : {statistics.mean(token_counts):.1f} token")
        print(f"   Std  : {statistics.stdev(token_counts):.1f} token")
        print(f"   >450 : {sum(1 for t in token_counts if t > 450)} chunk (sınır ihlali — 0 olmalı)")
        print("\nÖrnek chunk:")
        print(json.dumps(
            {k: v for k, v in chunks[0].items() if k != "text"},
            ensure_ascii=False, indent=2
        ))
        print(f"  text[:200]: {chunks[0]['text'][:200]}...")
    else:
        print("⚠️  Önce data/raw/ klasörüne PDF ekleyin.")
