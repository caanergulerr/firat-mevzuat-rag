"""
Her PDF'in .txt sidecar dosyasının ilk 500 karakterinden regulation_name çıkarmaya çalışır.
regulation_name_map.json oluşturmak için kullanılır.
"""
import sys, os, json, re
from pathlib import Path

DATA_DIR = Path("data/raw")

# Türkçe yönetmelik başlığı için regex — ilk satırlarda geçen tam başlık
TITLE_PATTERNS = [
    re.compile(r"(FIRAT\s+ÜNİVERSİTESİ\s+[A-ZÇĞİÖŞÜa-zçğışöüı\s\(\)\.\/\-]+(?:YÖNETMELİĞİ|YÖNERGESİ|KANUNU|ESASLARI|PROGRAMI|KURULU|KOMİSYON))", re.IGNORECASE),
    re.compile(r"(Fırat\s+Üniversitesi\s+[A-ZÇĞİÖŞÜa-zçğışöüı\s\(\)\.\/\-]+(?:Yönetmeliği|Yönergesi|Kanunu|Esasları|Programı))", re.IGNORECASE),
    re.compile(r"([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ\s\-\.]+(?:YÖNETMELİĞİ|YÖNERGESİ|ESASLARI|PROGRAMI|TÜZÜĞÜ))"),
]

result = {}
unknown = []

all_pdfs = sorted(DATA_DIR.glob("*.pdf"))
print(f"{len(all_pdfs)} PDF bulundu.\n")

for pdf_path in all_pdfs:
    txt_path = pdf_path.with_suffix(pdf_path.suffix + ".txt")
    pdf_name = pdf_path.name

    # İsimli PDF'ler — dosya adından türetebiliriz
    if not pdf_path.stem.isdigit():
        # Dosya adı zaten anlamlı
        human_name = pdf_path.stem.replace("_", " ").strip()
        result[pdf_name] = human_name
        continue

    # Numeric ID'li PDF'ler — .txt içeriğinden çıkarmaya çalış
    if not txt_path.exists():
        unknown.append(pdf_name)
        result[pdf_name] = pdf_path.stem  # fallback
        continue

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read(800)  # İlk 800 karakter yeterli

    found = None
    for pattern in TITLE_PATTERNS:
        m = pattern.search(content)
        if m:
            found = m.group(1).strip()
            # Çok uzun başlıkları kes
            if len(found) > 120:
                found = found[:120].rsplit(" ", 1)[0]
            break

    if found:
        result[pdf_name] = found
    else:
        result[pdf_name] = pdf_path.stem  # Bulunamazsa ID'yi koy
        unknown.append(pdf_name)

# JSON kaydet
out_path = Path("scripts/regulation_name_map.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"✅ {len(result)} PDF islendi -> {out_path}")
print(f"⚠️  {len(unknown)} PDF'de baslik bulunamadi (ID olarak kaldi):\n")
for u in unknown[:20]:
    print(f"   {u}")
if len(unknown) > 20:
    print(f"   ... ve {len(unknown)-20} tane daha")

print("\nOrnek eslesme:")
for k, v in list(result.items())[:8]:
    print(f"  {k[:30]:<32} -> {v[:60]}")
