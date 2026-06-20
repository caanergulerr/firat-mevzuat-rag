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

# Ragas modulleri
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

nest_asyncio.apply()

# Kac soru degerlendirilsin?
N_QUESTIONS = 20


def run_evaluation():
    # 1. Test veri setini yukle (comprehensive > eski)
    base = os.path.dirname(__file__)
    comp_path = os.path.join(base, "comprehensive_benchmark.json")
    old_path  = os.path.join(base, "benchmark_dataset.json")

    if os.path.exists(comp_path):
        dataset_path = comp_path
        print(f"[INFO] Kapsamli benchmark kullaniliyor (ilk {N_QUESTIONS} soru)")
    elif os.path.exists(old_path):
        dataset_path = old_path
        print("[UYARI] Kucuk benchmark kullaniliyor")
    else:
        print("[HATA] Benchmark dosyasi bulunamadi!")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    test_data = all_data[:N_QUESTIONS]
    print(f"[INFO] {len(test_data)} soru ile degerlendirme yapilacak.")

    # 2. RAG sistemini baslat
    print("\n[INFO] RAG Pipeline baslatiliyor...")
    pipeline = RAGPipeline()

    if not pipeline.is_ready():
        print("[HATA] ChromaDB hazir degil. Once: python scripts/embed_and_index.py")
        return

    questions     = []
    answers       = []
    contexts      = []
    ground_truths = []
    source_files  = []

    print("\n[INFO] Sorular RAG sistemine soruluyor...")
    for idx, item in enumerate(test_data):
        question = item["question"]
        expected = item["reference_answer"]
        src_file = item.get("expected_source_file", "bilinmiyor")

        print(f"  [{idx+1:2d}/{len(test_data)}] {question[:70]}...")

        try:
            result = pipeline.ask(question)
            questions.append(question)
            answers.append(result.answer)
            ctx = [c.text for c in result.retrieved_chunks] if result.retrieved_chunks else [""]
            contexts.append(ctx)
            ground_truths.append(expected)
            source_files.append(src_file)
        except Exception as e:
            print(f"    [HATA] Soru atlanıyor: {e}")

    print(f"\n[INFO] {len(questions)} soru basariyla islendi.")

    # 3. Ragas Dataset
    data = {
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data)

    # 4. LLM yapılandirmasi
    llm = None
    embeddings = None
    if os.getenv("OPENAI_API_KEY"):
        print("\n[INFO] Ragas icin OpenAI GPT-4o-mini kullaniliyor...")
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        llm = ChatOpenAI(model="gpt-4o-mini", max_retries=5)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    elif os.getenv("GOOGLE_API_KEY"):
        print("\n[INFO] Ragas icin Google Gemini kullaniliyor...")
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", max_retries=10)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    else:
        print("[HATA] OPENAI_API_KEY veya GOOGLE_API_KEY bulunamadi!")
        return

    print("\n[INFO] RAGAS degerlendirmesi basliyor (5-10 dakika surebilir)...")

    from ragas.run_config import RunConfig

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=1, max_retries=10, max_wait=60)
    )

    # 5. Once DataFrame'e donustur — yeni ragas versiyonunda .items() yok
    df = result.to_pandas()
    df["source_file"] = source_files[:len(df)]

    METRIC_COLS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    available_metrics = [c for c in METRIC_COLS if c in df.columns]

    print("\n" + "="*55)
    print("[SONUC] RAGAS DEGERLENDIRME SONUCLARI")
    print("="*55)
    for metric_name in available_metrics:
        value = float(df[metric_name].mean())
        bar = "#" * int(value * 20)
        print(f"  {metric_name:<22}: %{value*100:5.1f}  [{bar:<20}]")
    print("="*55)

    # 6. PDF bazli basari analizi
    print("\n[ANALIZ] PDF Bazli Basari Durumu:")
    print("-" * 55)
    pdf_groups = df.groupby("source_file")[["faithfulness", "answer_relevancy"]].mean()
    pdf_groups = pdf_groups.sort_values("faithfulness")
    for src, row in pdf_groups.iterrows():
        faith     = float(row.get("faithfulness", 0) or 0)
        relevancy = float(row.get("answer_relevancy", 0) or 0)
        status    = "ZAYIF" if faith < 0.5 else "IYI  "
        print(f"  [{status}] {src:<35} faith={faith:.2f}  rel={relevancy:.2f}")
    print("-" * 55)

    # 7. Kaydet
    output_path = os.path.join(base, "ragas_results.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\n[OK] Soru bazli detaylar kaydedildi: {output_path}")

    summary = {m: float(df[m].mean()) for m in available_metrics}
    summary["n_questions"] = len(questions)
    summary["dataset"] = os.path.basename(dataset_path)
    summary_path = os.path.join(base, "ragas_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[OK] Ozet kaydedildi: {summary_path}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_evaluation()
