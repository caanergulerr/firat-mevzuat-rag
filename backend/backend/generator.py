"""
generator.py
------------
Retrieval edilen chunk'ları kullanarak LLM ile kaynaklı cevap üretir.

Sistem, sadece verilen belge parçalarına dayanarak cevap verir.
Belgede bilgi yoksa "Bu konuda resmi bir hüküm bulamadım" der.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen Firat Universitesi'nin resmi dijital asistanisin.
Gorev: Ogrencinin sorusunu YALNIZCA asagida verilen belge parcalarindan yararlanarak, KISA ve DOGRUDAN yanitla.

KATI KURALLAR:
1. YALNIZCA verilen belge parcasindaki bilgileri kullan. Belgede YAZMAYANINI KESINLIKLE UYDURMA.
2. PDF'den bozuk gelen Turkce karakterleri baglamdan anla ve duzelt:
   'renci'='ogrenci', 'ift anadal'='cift anadal', 'art'='sart', 'bavuru'='basvuru', 'retim'='ogretim'
3. Cevabini 3-5 cumleyle sinirla. Soruyu dogrudan yanitla, uzun giris cumleleri yazma.
4. Cevabinin sonuna mutlaka kaynak ekle: "Kaynak: [Yonetmelik Adi], Madde [No]"
5. Belgede gercekten bilgi yoksa: "Bu konuda mevzuatta resmi bir hukum bulamadim. Ogrenci Isleri'ne basvurmanizi oneririm."
6. Ogrencinin gunluk dili ile resmi terimi eslestir: 'ustten ders'='ust yariyil', 'not ortalamasi'='GNO', 'okuldan atilma'='ilisik kesme', 'sinifi gecemem'='GNO esigi / basarisiz ders'."""

CONTEXT_TEMPLATE = """
--- Belge Parçası {i} ---
Kaynak: {citation}
İçerik: {text}
"""


def _build_context(chunks) -> str:
    """Retrieved chunk'ları LLM context string'ine dönüştürür.

    Not: chunk.text artık kırpılmıyor. chunker.py gerçek BERTurk
    tokenizer ile ≤450 token garantisi sağlıyor (~1200-1800 karakter).
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(CONTEXT_TEMPLATE.format(
            i=i,
            citation=chunk.citation(),
            text=chunk.text,   # artık tam metin — [:1000] hack'i kaldırıldı
        ))
    return "\n".join(parts)


def _chat_completion(client, model: str, system: str, user: str) -> str:
    """OpenAI-uyumlu chat completion çağrısı."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=500,   # Ozluk + tam cumle dengesi (faithfulness icin)
    )
    return response.choices[0].message.content


def generate_answer_groq(question: str, chunks: list) -> dict:
    """
    Groq API ile cevap üretir (openai paketi üzerinden, ücretsiz).
    Model: llama-3.3-70b-versatile — Türkçe destekli, günde 14.400 istek.
    """
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    context = _build_context(chunks)
    user_message = f"""Aşağıdaki resmi belge parçalarını kullanarak soruyu yanıtla.

BELGE PARÇALARI:
{context}

SORU: {question}"""

    answer = _chat_completion(client, "llama-3.3-70b-versatile", SYSTEM_PROMPT, user_message)
    sources = list({c.citation() for c in chunks})
    return {"answer": answer, "sources": sources, "model": "groq/llama-3.3-70b"}


def generate_answer_openai(question: str, chunks: list) -> dict:
    """OpenAI GPT-4o-mini ile cevap üretir."""
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    context = _build_context(chunks)
    user_message = f"""Aşağıdaki resmi belge parçalarını kullanarak soruyu yanıtla.

BELGE PARÇALARI:
{context}

SORU: {question}"""

    answer = _chat_completion(client, "gpt-4o-mini", SYSTEM_PROMPT, user_message)
    sources = list({c.citation() for c in chunks})
    return {"answer": answer, "sources": sources, "model": "gpt-4o-mini"}


def generate_answer_gemini(question: str, chunks: list) -> dict:
    """Google Gemini ile cevap üretir."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai paketi eksik: pip install google-generativeai")

    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    context = _build_context(chunks)
    prompt = f"""{SYSTEM_PROMPT}

BELGE PARÇALARI:
{context}

SORU: {question}"""

    response = model.generate_content(prompt)
    sources = list({c.citation() for c in chunks})
    return {"answer": response.text, "sources": sources, "model": "gemini-2.5-flash"}


def generate_answer(question: str, chunks: list) -> dict:
    """
    Mevcut API anahtarına göre uygun LLM'i seçer.
    Öncelik: OpenAI → Groq → Gemini → demo
    """
    if not chunks:
        return {
            "answer": "Bu konuda mevzuatımızda resmi bir hüküm bulamadım. Öğrenci İşleri Dairesi ile iletişime geçmenizi öneririm.",
            "sources": [],
            "model": "fallback",
        }

    if os.getenv("OPENAI_API_KEY"):
        return generate_answer_openai(question, chunks)
    elif os.getenv("GROQ_API_KEY"):
        return generate_answer_groq(question, chunks)
    elif os.getenv("GOOGLE_API_KEY"):
        return generate_answer_gemini(question, chunks)
    else:
        best = chunks[0]
        return {
            "answer": f"[Demo Mod — API anahtarı yok]\n\n{best.citation()} hükmüne göre:\n\n{best.text[:500]}...",
            "sources": [c.citation() for c in chunks],
            "model": "demo",
        }
