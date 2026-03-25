# Fırat Üniversitesi Mevzuat RAG Sistemi

> **NLP ve RAG mimarisi ile Fırat Üniversitesi yönetmeliklerine anında, kaynaklı cevap veren akıllı dijital asistan.**

---

## 🎯 Proje Özeti

Öğrencilerin "Mazeret sınavı hakkım var mı?", "Çift anadal için GPA şartı nedir?" gibi sorularını doğal dilde alıp, resmi PDF yönetmeliklerini okuyarak **Madde X'e göre** diye kaynak göstererek yanıtlayan bir yapay zeka asistanı.

Sistem asla uydurmaz — belgede yoksa "Bu konuda resmi bir hüküm bulamadım" der.

---

## 🏗️ Sistem Mimarisi

```
PDF Belgeler
    │
    ▼
[pdf_parser.py]  ──►  Madde bazlı metin çıkarma
    │
    ▼
[chunker.py]     ──►  Akıllı metin parçalama (madde + metadata)
    │
    ▼
[embed_and_index.py]  ──►  BERTurk Embedding → ChromaDB
    │
    ▼
Kullanıcı Sorusu
    │
    ▼
[retriever.py]   ──►  Semantik arama → Top-K ilgili madde
    │
    ▼
[generator.py]   ──►  LLM + retrieved chunks → Kaynaklı cevap
    │
    ▼
FastAPI REST API ──►  Chat Arayüzü (Frontend)
```

---

## 📁 Proje Yapısı

```
firat_mevzuat_rag/
│
├── data/
│   └── raw/                    # Fırat Üniversitesi PDF yönetmelikleri
│
├── scripts/
│   ├── pdf_parser.py           # PDF → yapılandırılmış metin
│   ├── chunker.py              # Metin parçalama
│   └── embed_and_index.py      # Embedding + ChromaDB indexleme
│
├── backend/
│   ├── retriever.py            # Semantik arama motoru
│   ├── generator.py            # LLM cevap üretici
│   ├── rag_pipeline.py         # Uçtan uca RAG pipeline
│   └── api.py                  # FastAPI endpoints
│
├── frontend/
│   ├── index.html              # Sohbet arayüzü
│   ├── style.css               # UI tasarımı
│   └── app.js                  # Frontend mantığı
│
├── evaluation/
│   ├── benchmark_dataset.json  # Test soru-cevap veri seti
│   ├── metrics.py              # Precision@K, ROUGE-L, MRR
│   └── run_evaluation.py       # Otomatik değerlendirme
│
├── docs/
│   └── paper_draft.md          # Akademik makale taslağı
│
├── .env.example                # Ortam değişkenleri şablonu
├── requirements.txt            # Python bağımlılıkları
└── README.md
```

---

## 🛠️ Kullanılan Teknolojiler

| Katman | Teknoloji |
|---|---|
| PDF Ayrıştırma | `pdfplumber`, `PyMuPDF` |
| Embedding (Türkçe) | `BERTurk` (`dbmdz/bert-base-turkish-cased`) |
| Vektör Veritabanı | `ChromaDB` |
| LLM | `GPT-4o-mini` / `Gemini` |
| API | `FastAPI` |
| Değerlendirme | `ROUGE-L`, `Precision@K`, `MRR` |
| Frontend | Vanilla HTML/CSS/JS |

---

## 🚀 Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/[kullanici]/firat_mevzuat_rag.git
cd firat_mevzuat_rag

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ortam değişkenlerini ayarla
copy .env.example .env
# .env dosyasını düzenleyip API anahtarını girin

# 5. PDF belgelerini yükle
# data/raw/ klasörüne Fırat Üni yönetmelik PDF'lerini koyun

# 6. İndexleme yap (ilk çalıştırma)
python scripts/embed_and_index.py

# 7. API'yi başlat
uvicorn backend.api:app --reload
# → http://localhost:8000

# 8. Arayüzü aç
# frontend/index.html dosyasını tarayıcıda aç
```

---

## 👥 Ekip

| İsim | Rol |
|---|---|
| Caner Güler | Scrum Master + Backend |
| Baran Arda Kandemir | Backend |
| Alperen Göral | Frontend |
| Zübeyde Mehlika Türktan | Dokümantasyon + Gereksinim Analizi |

---

## 📚 Hedef Yönetmelikler

- Fırat Üniversitesi Lisans Eğitim-Öğretim ve Sınav Yönetmeliği  
- Fırat Üniversitesi Çift Anadal ve Yandal Yönetmeliği  
- Fırat Üniversitesi Öğrenci Disiplin Yönetmeliği

---

## 📄 Akademik Çıktı

> *"Üniversite Mevzuat Belgelerinde Retrieval-Augmented Generation (RAG) Sistemlerinin Performans Analizi: Fırat Üniversitesi Örneği"*
