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

SYSTEM_PROMPT = """Sen Fırat Üniversitesi'nin resmi dijital asistanısın.
Görevin, öğrencilerin yönetmelik sorularını YALNIZCA sana verilen resmi belge parçalarına dayanarak yanıtlamaktır.

ÖNEMLİ KURALLAR:
1. Sadece verilen belge parçalarındaki bilgileri kullan. Hiçbir şeyi uydurma.
2. UYARI: Belgeler PDF'den çevrildiği için bazı metinlerdeki Türkçe karakterler bozuk veya eksik olabilir (Örn: 'ift anadal' = 'çift anadal', 'renci' = 'öğrenci', 'art' = 'şart', 'bavuru' = 'başvuru'). Bu mantığa göre bozuk kelimeleri onararak anlamlarını çıkar ve soruyu cevapla.
3. Her cevabın sonunda hangi maddeye dayandığını belirt. Örnek: "📖 Kaynak: Lisans Yönetmeliği, Madde 12"
4. Eğer sorunun cevabı verilen belgelerde yoksa, şunu söyle: "Bu konuda mevzuatımızda resmi bir hüküm bulamadım. Öğrenci İşleri'ne başvurmanızı öneririm."
5. Türkçe yanıt ver. Resmi ama anlaşılır bir dil kullan.
6. Madde numarasını her zaman belirt."""

CONTEXT_TEMPLATE = """
--- Belge Parçası {i} ---
Kaynak: {citation}
İçerik: {text}
"""


def _build_context(chunks) -> str:
    """Retrieved chunk'ları LLM context string'ine dönüştürür."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(CONTEXT_TEMPLATE.format(
            i=i,
            citation=chunk.citation(),
            text=chunk.text[:1000],  # Çok uzun chunk'ları kırp
        ))
    return "\n".join(parts)


def generate_answer_openai(question: str, chunks: list) -> dict:
    """
    OpenAI GPT-4o-mini ile cevap üretir.

    Returns:
        {"answer": str, "sources": [str], "model": str}
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except ImportError:
        raise ImportError("openai paketi eksik: pip install openai")

    context = _build_context(chunks)
    user_message = f"""Aşağıdaki resmi belge parçalarını kullanarak soruyu yanıtla.

BELGE PARÇALARI:
{context}

SORU: {question}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,  # Düşük temperature = tutarlı cevaplar
        max_tokens=600,
    )

    answer = response.choices[0].message.content
    sources = list({c.citation() for c in chunks})

    return {
        "answer": answer,
        "sources": sources,
        "model": "gpt-4o-mini",
    }


def generate_answer_gemini(question: str, chunks: list) -> dict:
    """
    Google Gemini ile cevap üretir (ücretsiz tier mevcut).

    Returns:
        {"answer": str, "sources": [str], "model": str}
    """
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
    answer = response.text
    sources = list({c.citation() for c in chunks})

    return {
        "answer": answer,
        "sources": sources,
        "model": "gemini-1.5-flash",
    }


def generate_answer(question: str, chunks: list) -> dict:
    """
    Mevcut API anahtarına göre uygun LLM'i seçer.

    Öncelik: OpenAI → Gemini
    Hiçbiri yoksa: basit kural tabanlı cevap döner.
    """
    if not chunks:
        return {
            "answer": "Bu konuda mevzuatımızda resmi bir hüküm bulamadım. Öğrenci İşleri Dairesi ile iletişime geçmenizi öneririm.",
            "sources": [],
            "model": "fallback",
        }

    if os.getenv("OPENAI_API_KEY"):
        return generate_answer_openai(question, chunks)
    elif os.getenv("GOOGLE_API_KEY"):
        return generate_answer_gemini(question, chunks)
    else:
        # API anahtarı yoksa retrieved chunk'ı döndür
        best = chunks[0]
        return {
            "answer": f"[Demo Mod — API anahtarı yok]\n\n{best.citation()} hükmüne göre:\n\n{best.text[:500]}...",
            "sources": [c.citation() for c in chunks],
            "model": "demo",
        }
