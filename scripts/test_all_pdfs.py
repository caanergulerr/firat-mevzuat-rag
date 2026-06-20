import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import sys

# Backend'i import edebilmek için yolu ekle
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from backend.rag_pipeline import RAGPipeline

load_dotenv(project_root / ".env")

import re

def generate_question_from_text(text: str) -> str:
    # Metinden kelimeleri al
    words = text.split()
    
    # Çok kısa metinler için basit bir soru
    if len(words) < 20:
        return f"Bu belgede '{' '.join(words[:5])}' hakkında ne söyleniyor?"
    
    # Metnin ortalarından anlamlı bir parça bul (başlıklardan vs. kaçınmak için ortadan alıyoruz)
    start_idx = len(words) // 4
    sample_phrase = " ".join(words[start_idx:start_idx+15])
    
    # Noktalama işaretlerini temizle
    sample_phrase = re.sub(r'[^\w\s]', '', sample_phrase).strip()
    
    return f"Yönetmelikte geçen '{sample_phrase}' ifadesi hangi bağlamda kullanılmaktadır? Açıklayınız."

def main():
    data_raw_dir = project_root / "data" / "raw"
    txt_files = list(data_raw_dir.glob("*.pdf.txt"))
    
    if not txt_files:
        print("data/raw klasöründe hiç .pdf.txt dosyası bulunamadı.")
        return
    
    print(f"Toplam {len(txt_files)} dosya bulundu. RAG Pipeline yükleniyor...")
    pipeline = RAGPipeline()
    
    results = []
    out_file = project_root / "test_results.json"
    
    print("Test başlıyor...")
    
    for i, txt_file in enumerate(txt_files):
        pdf_name = txt_file.name.replace(".txt", "")
        print(f"\n[{i+1}/{len(txt_files)}] İşleniyor: {pdf_name}")
        
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read(1500) # Soru üretebilmek için ilk 1500 karakteri al
            
        if not content.strip():
            print("Dosya boş, atlanıyor.")
            results.append({
                "pdf_name": pdf_name,
                "status": "EMPTY_FILE",
                "question": "",
                "sources": []
            })
            continue
            
        # 1. Soru üret
        print("Soru üretiliyor...")
        question = generate_question_from_text(content)
        print(f"Soru: {question}")
        
        # 2. Pipeline'a sor
        print("Sistemden cevap bekleniyor...")
        start_time = time.time()
        try:
            ans = pipeline.ask(question)
            latency = time.time() - start_time
            
            # 3. Sonucu değerlendir
            returned_sources = ans.sources
            expected_found = any(pdf_name in s for s in returned_sources)
            
            # Cevapta olumsuz bir durum var mı kontrol et
            ans_lower = ans.answer.lower()
            if "bilgi bulamadım" in ans_lower or ("verilen metinlerde" in ans_lower and "yok" in ans_lower):
                status = "NO_ANSWER"
            elif expected_found:
                status = "SUCCESS"
            else:
                status = "WRONG_SOURCE"
                
            print(f"Durum: {status} ({latency:.2f} sn)")
            print(f"Dönen Kaynaklar: {returned_sources}")
            
            results.append({
                "pdf_name": pdf_name,
                "question": question,
                "answer": ans.answer,
                "expected_source": pdf_name,
                "returned_sources": returned_sources,
                "status": status,
                "latency_s": round(latency, 2)
            })
        except Exception as e:
            print(f"Pipeline hatası: {e}")
            results.append({
                "pdf_name": pdf_name,
                "question": question,
                "answer": str(e),
                "expected_source": pdf_name,
                "returned_sources": [],
                "status": "ERROR"
            })
            
        # Her adımda sonuçları kaydet (çökerse veri kaybetmemek için)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        time.sleep(1) # API Rate Limit'e takılmamak için
        
    # Özet yazdır
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    wrong_source_count = sum(1 for r in results if r["status"] == "WRONG_SOURCE")
    no_answer_count = sum(1 for r in results if r["status"] == "NO_ANSWER")
    error_count = sum(1 for r in results if r["status"] in ["ERROR", "EMPTY_FILE"])
    
    print("\n" + "="*40)
    print("TEST ÖZETİ")
    print("="*40)
    print(f"Toplam Test Edilen PDF: {len(results)}")
    print(f"✅ Başarılı (SUCCESS): {success_count}")
    print(f"⚠️ Yanlış Kaynak (WRONG_SOURCE): {wrong_source_count}")
    print(f"❌ Cevap Yok (NO_ANSWER): {no_answer_count}")
    print(f"❌ Hatalı/Boş (ERROR/EMPTY): {error_count}")
    print(f"Tüm sonuçlar detaylı olarak kaydedildi: {out_file}")

if __name__ == "__main__":
    main()
