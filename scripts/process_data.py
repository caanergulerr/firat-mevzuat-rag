import sys
import json
import logging
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.pdf_parser import parse_all_pdfs
from scripts.chunker import chunk_all_articles

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("PDF'ler taranıyor ve parse ediliyor...")
    # Yeni taşıdığımız dizin
    articles = parse_all_pdfs("data/raw/yönetmelikler")
    
    if not articles:
        logger.error("Hiç madde ayıklanamadı!")
        return

    logger.info("Metinler (Maddeler) chunk'lara bölünüyor...")
    chunks = chunk_all_articles(articles)
    
    # Chunk JSON çıktısını kontrol edebilmemiz için kaydet
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    json_path = processed_dir / "chunks.json"
    
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        
    logger.info(f"\n✅ İşlem Tamamlandı. Toplam {len(chunks)} chunk üretildi ve '{json_path}' dosyasına başarıyla kaydedildi.")

if __name__ == "__main__":
    main()
