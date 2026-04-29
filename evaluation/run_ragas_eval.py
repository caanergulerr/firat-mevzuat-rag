import os
import json
import asyncio
import nest_asyncio
import pandas as pd
from datasets import Dataset

# Proje dizinini ekle
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.rag_pipeline import RAGPipeline

# Ragas modülleri
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

# Colab/Jupyter vb. ortamlarda asenkron loop'ların çalışması için (opsiyonel ama sağlıklı)
nest_asyncio.apply()

def run_evaluation():
    # 1. Test veri setini yükle
    dataset_path = os.path.join(os.path.dirname(__file__), "benchmark_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Hata: Veri seti bulunamadı -> {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    # 2. RAG sistemini başlat
    print("RAG Pipeline başlatılıyor...")
    pipeline = RAGPipeline()
    
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    
    print("\nTest veri setindeki sorular RAG sistemine soruluyor...")
    for idx, item in enumerate(test_data):
        question = item["question"]
        expected_answer = item["reference_answer"]
        
        print(f"[{idx+1}/{len(test_data)}] Soru: {question}")
        
        # Sistemi sorgula
        result = pipeline.ask(question)
        
        questions.append(question)
        answers.append(result.answer)
        # Ragas contexts list of lists of strings bekler
        contexts.append([c.text for c in result.retrieved_chunks])
        ground_truths.append(expected_answer)

    # 3. Ragas Dataset formatına çevir
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(data)

    # 4. LLM yapılandırması (Gemini veya OpenAI)
    llm = None
    embeddings = None
    if os.getenv("GOOGLE_API_KEY"):
        print("\nRagas metrikleri için Google Gemini modeli kullanılıyor...")
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", max_retries=15)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
    print("\n[BILGI] Ragas degerlendirmesi basliyor (API limitlerine bagli olarak 1-2 dakika surebilir)...")
    
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ]
    
    from ragas.run_config import RunConfig
    
    # Değerlendirmeyi çalıştır
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=1, max_retries=10, max_wait=60)
    )
    
    print("\n" + "="*50)
    print("[SONUC] RAGAS DEGERLENDIRME SONUCLARI")
    print("="*50)
    for metric_name, value in result.items():
        print(f"- {metric_name}: %{value * 100:.2f}")
    print("="*50)
    
    # Detaylı sonuçları CSV'ye kaydet
    df = result.to_pandas()
    output_path = os.path.join(os.path.dirname(__file__), "ragas_results.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"[BILGI] Soru bazlı tüm detaylar kaydedildi: {output_path}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_evaluation()
