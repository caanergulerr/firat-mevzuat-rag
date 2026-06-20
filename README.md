---
title: Firat Mevzuat RAG
emoji: 📖
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
---

# Fırat Üniversitesi Mevzuat RAG Sistemi

> **NLP ve RAG mimarisi ile Fırat Üniversitesi yönetmeliklerine anında, kaynaklı cevap veren akıllı dijital asistan.**

---

## 🎯 Proje Özeti

Öğrencilerin "Mazeret sınavı hakkım var mı?", "Çift anadal için GPA şartı nedir?" gibi sorularını doğal dilde alıp, resmi PDF yönetmeliklerini okuyarak **Madde X'e göre** diye kaynak göstererek yanıtlayan bir yapay zeka asistanı.

Sistem asla uydurmaz — belgede yoksa "Bu konuda resmi bir hüküm bulamadım" der.

**Veri tabanı:** 143 PDF yönetmelik belgesi → 3.144 chunk → BM25 + ChromaDB hibrit indeks

---

## 📊 Değerlendirme Sonuçları

### RAGAS Metrikleri *(60 soruluk benchmark, GPT-4o-mini yargıcı)*

| Metrik | Sonuç | Açıklama |
|--------|:-----:|----------|
| **Context Recall** | **%95.8** | Sistemin doğru maddeyi bulma oranı |
| **Context Precision** | **%78.5** | Getirilen chunk'ların isabetlilik oranı |
| **Faithfulness** | **%70.8** | Cevabın belgeye sadık olma oranı |
| **Answer Relevancy** | **%52.5** | Cevabın soruyla uyumu |

### Ablation Study — Retrieval Stratejisi Karşılaştırması *(60 sorgu, 60 farklı PDF)*

| Strateji | Precision@1 | Recall@5 | MRR |
|----------|:-----------:|:--------:|:---:|
| **BM25 Ağırlıklı Hybrid (0.2/0.8)** ✅ | **0.567** | **0.800** | **0.667** |
| Eşit Hybrid (0.5/0.5) | 0.400 | 0.700 | 0.516 |
| Semantik Ağırlıklı (0.6/0.4) | 0.317 | 0.383 | 0.347 |
| Sadece Semantik | 0.150 | 0.300 | 0.198 |

> **Temel Bulgu:** Yönetmelik metinleri "Madde 13", "GNO", "azami süre" gibi teknik terimler içerdiğinden BM25 anahtar kelime eşleştirmesi, semantik vektör aramasını belirgin biçimde geride bırakmıştır. Bu bulgu hukuki NLP literatürüyle uyumludur.

---

## 🏗️ Sistem Mimarisi

```
PDF Belgeler (143 adet)
    │
    ▼
[pdf_parser.py]       ──►  pdfplumber ile madde bazlı metin çıkarma
    │
    ▼
[chunker.py]          ──►  BERTurk tokenizer ile ≤450 token akıllı parçalama
    │                       (3.144 chunk, madde numarası + kaynak metadata)
    ▼
[embed_and_index.py]  ──►  BERTurk Embedding → ChromaDB vektör DB
                      ──►  BM25Okapi keyword indeksi (chunks.json)
    │
    ▼
Kullanıcı Sorusu
    │
    ▼
[retriever.py]        ──►  BM25 (0.8) + Semantik (0.2) Hibrit Arama → Top-5 chunk
    │
    ▼
[generator.py]        ──►  LLM (Groq / OpenAI / Gemini) + chunks → Kaynaklı cevap
    │
    ▼
FastAPI REST API      ──►  Chat Arayüzü (Vanilla HTML/CSS/JS)
```

---

## 📁 Proje Yapısı

```
firat-mevzuat-rag/
│
├── data/
│   ├── raw/                          # Fırat Üniversitesi PDF yönetmelikleri (143 adet)
│   └── processed/
│       └── chunks.json               # 3.144 chunk (BM25 indeksi için)
│
├── scripts/
│   ├── pdf_parser.py                 # PDF → yapılandırılmış madde metni
│   ├── chunker.py                    # BERTurk tokenizer tabanlı parçalama
│   ├── embed_and_index.py            # Embedding + ChromaDB indexleme
│   ├── generate_benchmark.py         # GPT-4o-mini ile sentetik test seti üretimi
│   └── regulation_name_map.json      # PDF dosya adı → yönetmelik adı eşlemesi
│
├── backend/
│   ├── retriever.py                  # BM25 + Semantik hibrit arama motoru
│   ├── generator.py                  # LLM cevap üretici (Groq/OpenAI/Gemini)
│   ├── rag_pipeline.py               # Uçtan uca RAG pipeline
│   └── api.py                        # FastAPI endpoints
│
├── frontend/
│   ├── index.html                    # Sohbet arayüzü
│   ├── style.css                     # UI tasarımı
│   └── app.js                        # Frontend mantığı
│
├── evaluation/
│   ├── comprehensive_benchmark.json  # 60 soruluk sentetik test veri seti
│   ├── ragas_results.csv             # Soru bazlı RAGAS metrikleri
│   ├── ragas_summary.json            # Özet metrikler
│   ├── ablation_results.json         # 5 retrieval modu karşılaştırması
│   ├── run_ragas_eval.py             # RAGAS değerlendirme scripti
│   └── run_ablation.py               # Ablation study scripti
│
├── .env.example                      # Ortam değişkenleri şablonu
├── requirements.txt                  # Python bağımlılıkları
├── Dockerfile                        # Docker imajı
└── README.md
```

---

## 🛠️ Kullanılan Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| PDF Ayrıştırma | `pdfplumber`, `PyMuPDF` |
| Tokenizer | `BERTurk` (`dbmdz/bert-base-turkish-cased`) |
| Keyword Arama | `rank-bm25` (BM25Okapi) |
| Vektör Veritabanı | `ChromaDB` |
| LLM | `Groq / llama-3.3-70b` (birincil) · `GPT-4o-mini` · `Gemini 2.5 Flash` |
| API | `FastAPI` |
| Değerlendirme | `RAGAS` (faithfulness, relevancy, precision, recall) |
| Frontend | Vanilla HTML / CSS / JS |

---

## 🚀 Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/caanergulerr/firat-mevzuat-rag.git
cd firat-mevzuat-rag

# 2. Sanal ortam oluştur
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ortam değişkenlerini ayarla
copy .env.example .env
# .env dosyasını açıp API anahtarınızı girin (GROQ_API_KEY veya OPENAI_API_KEY)

# 5. PDF belgelerini yükle
# data/raw/ klasörüne Fırat Üniversitesi yönetmelik PDF'lerini koyun

# 6. İndexleme yap (ilk çalıştırma, ~10-15 dk)
python scripts/embed_and_index.py

# 7. API'yi başlat
uvicorn backend.api:app --reload
# → http://localhost:8000

# 8. Arayüzü aç
# frontend/index.html dosyasını tarayıcıda aç
# veya: http://localhost:8000 üzerinden (static dosyalar API tarafından servis edilir)
```

### Değerlendirme Çalıştırma

```bash
# Sentetik benchmark üret (OPENAI_API_KEY gerekli)
python scripts/generate_benchmark.py

# Ablation study (5 retrieval modu karşılaştırması)
python evaluation/run_ablation.py

# RAGAS değerlendirmesi (~15 dk, OPENAI_API_KEY gerekli)
python evaluation/run_ragas_eval.py
```

---

## 👥 Ekip

| İsim | Rol |
|------|-----|
| Caner Güler | Scrum Master + Backend |
| Baran Arda Kandemir | Backend |
| Alperen Göral | Frontend |
| Zübeyde Mehlika Türktan | Dokümantasyon + Gereksinim Analizi |

---

## 📚 Kapsanan Yönetmelikler

143 PDF yönetmelik belgesi dahil olmak üzere:

- Fırat Üniversitesi Lisans Eğitim-Öğretim ve Sınav Yönetmeliği
- Fırat Üniversitesi Lisansüstü Eğitim-Öğretim Yönetmeliği
- Fırat Üniversitesi Çift Anadal ve Yandal Yönetmeliği
- Fırat Üniversitesi Öğrenci Disiplin Yönetmeliği
- ve 139 adet diğer yönetmelik / yönerge

---

## 📄 Akademik Çıktı

> *"Üniversite Mevzuat Belgelerinde Retrieval-Augmented Generation (RAG) Sistemlerinin Performans Analizi: Fırat Üniversitesi Örneği"*
