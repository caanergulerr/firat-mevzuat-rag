import json
import random
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_TEMPLATE = """Sen Fırat Üniversitesi mevzuat uzmanısın.
Aşağıdaki yönetmelik maddesini okuyup, bir öğrencinin bu maddeye dayanarak sorabileceği ZOR, SPESİFİK ve SENARYO TABANLI bir soru üret. 
Ayrıca bu soruya tam olarak bu maddedeki bilgilere dayanarak verilecek doğru cevabı (reference_answer) üret.

KURAL 1: Soru doğrudan maddenin içindeki spesifik bir kuralı veya sayıyı sorgulamalıdır (örn: "Kaçıncı dönemden sonra...", "GNO en az kaç olmalı ki...").
KURAL 2: Genel geçer veya çok basit ("Yaz okulu nedir?") sorular üretme. Öğrenci ağzından sor (örn: "Ortalamam 1.80'in altındayken üstten ders alabilir miyim?").
KURAL 3: Yanıtı her zaman JSON formatında ver. Sadece JSON döneceksin, markdown falan kullanma.

Madde:
{text}

Beklenen JSON Formatı:
{{
  "question": "Öğrenci ağzından zor senaryo sorusu",
  "reference_answer": "Maddeye dayalı net ve resmi cevap"
}}
"""

def generate_question(text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that strictly outputs JSON."},
                {"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=300
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

def main():
    chunks_path = Path("data/processed/chunks.json")
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    print(f"Toplam {len(chunks)} chunk yüklendi.")
    
    # Çok kısa chunk'ları ele (içerik yetersiz olabilir)
    valid_chunks = [c for c in chunks if len(c.get("text", "")) > 150]
    print(f"Geçerli (150+ karakter) chunk sayısı: {len(valid_chunks)}")
    
    # Belgelere göre grupla ki çeşitli belgelerden soru gelsin
    # NOT: chunks.json'da alanlar doğrudan üst seviyede (metadata altında değil)
    by_file = {}
    for c in valid_chunks:
        src = c.get("source_file") or c.get("metadata", {}).get("source_file", "unknown")
        if src not in by_file:
            by_file[src] = []
        by_file[src].append(c)
        
    print(f"Farklı PDF sayısı: {len(by_file)}")
    
    # Her dosyadan 1 chunk seçerek toplam 60 farklı PDF'den soru üret
    TARGET = 60
    selected_chunks = []
    file_keys = list(by_file.keys())
    random.shuffle(file_keys)
    
    for f in file_keys:
        candidates = by_file[f]
        selected_chunks.append(random.choice(candidates))
        if len(selected_chunks) >= TARGET:
            break
            
    print(f"\n{len(selected_chunks)} farklı belgeden chunk rastgele seçildi.")
    
    benchmark = []
    failed = 0
    
    print("OpenAI gpt-4o-mini ile sorular üretiliyor (yaklaşık 2-3 dakika sürebilir)...")
    for i, chunk in enumerate(tqdm(selected_chunks)):
        text = chunk.get("text", "")
        # Alanlar doğrudan üst seviyede
        article_no     = chunk.get("article_no") or chunk.get("metadata", {}).get("article_no", "")
        source_file    = chunk.get("source_file") or chunk.get("metadata", {}).get("source_file", "")
        regulation_name = chunk.get("regulation_name") or chunk.get("metadata", {}).get("regulation_name", "")
        
        result = generate_question(text)
        if result and "question" in result and "reference_answer" in result:
            benchmark.append({
                "id": len(benchmark) + 1,
                "question": result["question"],
                "expected_articles": [article_no] if article_no else [],
                "expected_source_file": source_file,
                "expected_regulation": regulation_name,
                "reference_answer": result["reference_answer"],
                "source_text": text[:300]  # Debug için kaynak metni de ekle
            })
        else:
            failed += 1
            
        time.sleep(0.1) # Rate limit koruması
        
    out_path = Path("evaluation/comprehensive_benchmark.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)
        
    print(f"\n[OK] {len(benchmark)} soruluk kapsamli test veri seti olusturuldu: {out_path}")
    if failed:
        print(f"[UYARI] {failed} chunk icin LLM sorusu uretilemedi (API hatasi).")

if __name__ == "__main__":
    main()
