"""
generator.py
------------
Direct API Call (Requests) versiyonu. 
SDK hatalarını baypas eder.
"""

import os
import logging
import requests
import json
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen Fırat Üniversitesi'nin resmi dijital asistanısın.
Görevin, öğrencilerin yönetmelik sorularını YALNIZCA sana verilen resmi belge parçalarına dayanarak yanıtlamaktır.

ÖNEMLİ KURALLAR:
1. Sadece verilen belge parçalarındaki bilgileri kullan. Hiçbir şeyi uydurma.
2. Her cevabın sonunda hangi maddeye dayandığını belirt.
3. Bilgi yoksa "Bu konuda mevzuatımızda resmi bir hüküm bulamadım." de."""

def _build_context(chunks) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"--- Belge {i} ---\nKaynak: {chunk.citation()}\nİçerik: {chunk.text[:1000]}")
    return "\n".join(parts)

def generate_answer_gemini_direct(question: str, chunks: list) -> dict:
    """Google Gemini API'sine SDK kullanmadan doğrudan istek atar."""
    api_key = os.getenv("GOOGLE_API_KEY")
    # API versiyonunu v1beta yerine v1 veya v1beta (model uyumlu) olarak zorluyoruz
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    context = _build_context(chunks)
    prompt_text = f"{SYSTEM_PROMPT}\n\nBELGE PARÇALARI:\n{context}\n\nSORU: {question}"

    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "topK": 40,
            "maxOutputTokens": 1024,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Google API yanıt yapısından cevabı çıkar
        answer = data['candidates'][0]['content']['parts'][0]['text']
        
        return {
            "answer": answer,
            "sources": list({c.citation() for c in chunks}),
            "model": "gemini-1.5-flash-direct",
        }
    except Exception as e:
        logger.error(f"Gemini Direct API Hatası: {str(e)}")
        # Eğer 1.5 Flash hata verirse 1.0 Pro'yu dene
        return {"answer": f"Bir hata oluştu, lütfen API anahtarınızı veya internetinizi kontrol edin. Detay: {str(e)}", "sources": [], "model": "error"}

def generate_answer(question: str, chunks: list) -> dict:
    """API anahtarına göre uygun LLM'i seçer."""
    if not chunks:
        return {"answer": "Bu konuda resmi bir hüküm bulamadım.", "sources": [], "model": "fallback"}

    # Gemini anahtarı varsa doğrudan istek metodunu kullan
    if os.getenv("GOOGLE_API_KEY"):
        logger.info("Gemini Direct API ile cevap üretiliyor...")
        return generate_answer_gemini_direct(question, chunks)
    
    # OpenAI kısmı (varsa) buraya eklenebilir
    
    else:
        best = chunks[0]
        return {
            "answer": f"[Demo Mod] {best.citation()} hükmüne göre: {best.text[:300]}...",
            "sources": [c.citation() for c in chunks],
            "model": "demo",
        }