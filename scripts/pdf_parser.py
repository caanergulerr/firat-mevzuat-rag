"""
pdf_parser.py
-------------
Fırat Üniversitesi yönetmelik PDF'lerini madde bazında ayrıştırır.

Her çıktı şu formatta bir dict listesidir:
[
    {
        "regulation_name": "Lisans Eğitim Öğretim Yönetmeliği",
        "article_no": "5",
        "article_title": "Kayıt ve Kabul",
        "text": "Madde 5 — ...",
        "source_file": "lisans_yonetmelik.pdf",
        "page": 3
    },
    ...
]
"""

import re
import json
import logging
from pathlib import Path

import pdfplumber
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Madde başlığı için regex (Türkçe yönetmelik formatı)
ARTICLE_PATTERN = re.compile(
    r"(MADDE\s+(\d+)\s*[–\-—]\s*(.*?))\n",
    re.IGNORECASE
)


def extract_text_pdfplumber(pdf_path: str) -> str:
    """pdfplumber ile PDF'den ham metin çıkarır. Tablo algılama destekli."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
    return full_text


def extract_text_pymupdf(pdf_path: str) -> str:
    """PyMuPDF ile PDF'den ham metin çıkarır. Daha hızlı, bazı PDFler için daha iyi."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()
    return full_text


def parse_articles(text: str, regulation_name: str, source_file: str) -> list[dict]:
    """
    Ham metni madde bazında parçalara ayırır.
    Her madde ayrı bir dict olarak döner.
    """
    articles = []
    matches = list(ARTICLE_PATTERN.finditer(text))

    for i, match in enumerate(matches):
        article_no = match.group(2)
        article_title = match.group(3).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        article_text = text[start:end].strip()

        articles.append({
            "regulation_name": regulation_name,
            "article_no": article_no,
            "article_title": article_title,
            "text": article_text,
            "source_file": source_file,
            "char_count": len(article_text),
        })

    logger.info(f"'{regulation_name}' dosyasında {len(articles)} madde bulundu.")
    return articles


def parse_pdf(pdf_path: str, regulation_name: str = None) -> list[dict]:
    """
    PDF dosyasını okur ve madde listesi döner.

    Args:
        pdf_path: PDF dosyasının yolu
        regulation_name: Yönetmelik adı (None ise dosya adından türetilir)

    Returns:
        Madde dict listesi
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF bulunamadı: {pdf_path}")

    if regulation_name is None:
        regulation_name = path.stem.replace("_", " ").title()

    logger.info(f"PDF işleniyor: {pdf_path}")

    # Önce pdfplumber dene, sonra PyMuPDF
    try:
        text = extract_text_pdfplumber(pdf_path)
    except Exception as e:
        logger.warning(f"pdfplumber başarısız ({e}), PyMuPDF deneniyor...")
        text = extract_text_pymupdf(pdf_path)

    if not text.strip():
        raise ValueError(f"PDF'den metin çıkarılamadı: {pdf_path}")

    articles = parse_articles(text, regulation_name, path.name)
    return articles


def parse_all_pdfs(data_dir: str = "data/raw") -> list[dict]:
    """
    data/raw/ klasöründeki tüm PDF'leri işler.

    Returns:
        Tüm yönetmeliklerin birleşik madde listesi
    """
    data_path = Path(data_dir)
    pdf_files = list(data_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"'{data_dir}' klasöründe PDF bulunamadı!")
        return []

    all_articles = []
    for pdf_file in pdf_files:
        try:
            articles = parse_pdf(str(pdf_file))
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Hata ({pdf_file.name}): {e}")

    logger.info(f"Toplam {len(all_articles)} madde işlendi ({len(pdf_files)} PDF).")
    return all_articles


if __name__ == "__main__":
    # Test — önce data/raw/ klasörüne bir PDF koyun
    articles = parse_all_pdfs("data/raw")
    if articles:
        print(f"\n✅ {len(articles)} madde ayrıştırıldı.")
        print("\nÖrnek madde:")
        print(json.dumps(articles[0], ensure_ascii=False, indent=2))
    else:
        print("⚠️  data/raw/ klasörüne Fırat Üniversitesi yönetmelik PDF'lerini ekleyin.")
