# Değişiklik: PDF Metin Analizi ve Tarama (Scanned) Belge Tespiti
**Tarih:** 31 Mart 2026
**Zorluk Derecesi:** Orta
**Durum:** Tespit Edildi, Kısmi Çözüldü

## Karşılaşılan Sorun
Projedeki `yönetmelikler` klasöründe yer alan 143 adet PDF dosyasının hepsinin düz metin (text-layer) içerdiği varsayılmıştı. Ancak bazı dosyalardan metin alınamadığı veya çok az/boş döndüğü fark edildi. Bu durum, RAG sisteminin (Retrieval-Augmented Generation) bazı belgelerde doğru cevap verememesine ve eksik bilgi üretmesine yol açacaktı.

## Neden Oldu?
Bazı PDF belgeleri dijital ortamda kelime işlemciler (Word vb.) ile elektronik olarak oluşturulmamış; ıslak imzalı belgelerin **tarayıcıdan (scanner) fiziksel olarak geçirilmesiyle** bir "fotoğraf" (görüntü) formatında PDF'e dönüştürülmüş. Bu nedenle standart RAG ve PDF okuyucu kütüphaneler harfleri okuyamadı.

## Alınan Aksiyon ve Eklenen Kütüphaneler
1. Sorunun boyutunu anlamak için **Node.js** tabanlı bir analiz scripti yazılmasına karar verildi.
2. Sadece PDF okuma işlemi için projeye geçici olarak `"pdf-parse" (v1.1.1)` kütüphanesi indirildi.
3. `temp_pdf_parser/check_pdfs.js` isimli script tüm belgeleri taradı ve şu sonucu verdi:
   - **Toplam PDF:** 143
   - **Sorunsuz, Metin İçeren PDF Sayısı:** 137
   - **Sadece Görsel İçeren (Sorunlu) PDF Sayısı:** 6 adet

## Takım Arkadaşlarına (ve Yapay Zeka Asistanlarına) Not
Sistemde eksik metin bırakmamak adına, 6 adet sorunlu dosya tespit edilmiştir. İlerleyen aşamalarda **Python Tesseract OCR** (Optik Karakter Tanıma) entegre edilebilir veya proje sunumuna/demo kısmına yetiştirmek adına bu 6 dosya manuel olarak el ile metne dönüştürülüp veri setine katılabilir. Her halükarda veri setindeki kalite kontrolünün RAG mimarisindeki önemi kanıtlanmış ve sistemdeki büyük bir 'hayalet' hata önlenmiştir.
