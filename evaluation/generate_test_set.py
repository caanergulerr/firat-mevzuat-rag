"""
generate_test_set.py
--------------------
Her PDF'in .txt dosyasini okur, Gemini'ye gonderir ve
o belgeden ogrencilerin sorabilecegi soru-cevap ciftleri uretir.
Sonucu evaluation/test_set.json ve test_set.csv olarak kaydeder.

Model: gemini-1.5-flash (gunluk 1500 istek - ucretsiz tier)

Calistirmak icin:
    venv\Scripts\python.exe evaluation/generate_test_set.py
"""

import os
import json
import time
import csv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_RAW_DIR = Path("data/raw")
OUTPUT_DIR = Path("evaluation")
OUTPUT_JSON = OUTPUT_DIR / "test_set.json"
OUTPUT_CSV = OUTPUT_DIR / "test_set.csv"

PROMPT_TEMPLATE = """Asagida bir universite yonetmeliginin bir bolumunu veriyorum.
Bu belgeyi okuyan bir ogrencinin sorabilecegi GERCEKCI sorular uret.

Kuralllar:
- Sorular ogrencinin gercekte soracagi gunluk dilde olsun
  (ornek: "ustten ders alabilir miyim?", "mazeret sinavi icin ne lazim?")
- Her soru icin belgeden gelen dogru cevabi yaz
- Hangi madde numarasindan geldigini belirt
- Kac soru uretecegini asagida belirttim

Cikti formati (kesinlikle bu JSON formatinda ver, baska hicbir sey yazma):
[
  {{
    "question": "...",
    "answer": "...",
    "article_no": "Madde X",
    "source_file": "{filename}"
  }}
]

Uretilecek soru sayisi: {num_questions}

BELGE:
{content}
"""

def get_num_questions(content_length: int) -> int:
    """Belge uzunluguna gore soru sayisi belirle."""
    if content_length < 2000:
        return 2
    elif content_length < 5000:
        return 3
    elif content_length < 10000:
        return 5
    else:
        return 7

def generate_questions_for_file(model, txt_path: Path) -> list:
    """Tek bir .txt dosyasi icin soru-cevap ciftleri uretir."""
    content = txt_path.read_text(encoding="utf-8").strip()

    if len(content) < 200:
        print(f"  ATLA (cok kisa): {txt_path.name}")
        return []

    # Cok uzun belgeleri kisalt (Gemini token limiti)
    if len(content) > 8000:
        content = content[:8000] + "\n...(kisaltildi)"

    num_q = get_num_questions(len(content))
    filename = txt_path.name.replace(".pdf.txt", "")

    prompt = PROMPT_TEMPLATE.format(
        filename=filename,
        num_questions=num_q,
        content=content
    )

    try:
        for attempt in range(4):  # Maks 4 deneme
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.4, "max_output_tokens": 2000}
                )
                break  # Basarili, donguden cik
            except Exception as ex:
                if "429" in str(ex) and attempt < 3:
                    wait = 60 * (attempt + 1)  # 60s, 120s, 180s
                    print(f"  Rate limit - {wait}s bekleniyor...")
                    time.sleep(wait)
                else:
                    raise
        raw = response.text.strip()

        # JSON blogu temizle
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        questions = json.loads(raw)
        return questions

    except Exception as e:
        print(f"  HATA ({txt_path.name}): {e}")
        return []


def main():
    import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY bulunamadi! .env dosyasini kontrol et.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Mevcut dosyayi yukle (kaldigi yerden devam etmek icin)
    all_questions = []
    processed_files = set()
    if OUTPUT_JSON.exists():
        all_questions = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        processed_files = {q["source_file"] for q in all_questions}
        print(f"Mevcut dosyadan {len(all_questions)} soru yuklendi. Devam ediliyor...")

    txt_files = sorted(DATA_RAW_DIR.glob("*.pdf.txt"))
    total = len(txt_files)
    print(f"\nToplam {total} .txt dosyasi bulundu.\n")

    for i, txt_path in enumerate(txt_files, 1):
        filename = txt_path.name.replace(".pdf.txt", "")

        if filename in processed_files:
            print(f"[{i}/{total}] ATLA (zaten islendi): {filename[:50]}")
            continue

        print(f"[{i}/{total}] Isleniyor: {filename[:60]}")

        questions = generate_questions_for_file(model, txt_path)

        if questions:
            all_questions.extend(questions)
            processed_files.add(filename)
            print(f"  -> {len(questions)} soru eklendi (toplam: {len(all_questions)})")

            # Her dosyadan sonra kaydet (kesmede veri kaybi olmasin)
            OUTPUT_JSON.write_text(
                json.dumps(all_questions, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        else:
            print(f"  -> Soru uretilemedi")

        # Rate limit icin bekle (dakikada ~60 istek limiti)
        time.sleep(1.5)

    # CSV olarak da kaydet
    if all_questions:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["question", "answer", "article_no", "source_file"])
            writer.writeheader()
            writer.writerows(all_questions)

    print(f"\n{'='*60}")
    print(f"TAMAMLANDI!")
    print(f"Toplam soru: {len(all_questions)}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"CSV:  {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
