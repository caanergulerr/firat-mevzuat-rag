# Değişiklik: Node.js Tabanlı Tesseract OCR Entegrasyonu
**Tarih:** 31 Mart 2026
**Efor:** Orta/Hızlı
**Durum:** Tamamlandı

## Yapılan İşlem
Önceki kayıtta (`01-pdf-gorsel-okuma-sorunu.md`) bahsedilen 6 adet "fotoğraftan oluşan" PDF krizini çözmek için RAG altyapısına OCR (Görüntü İşleme) yeteneği eklendi.

## Neden Harici Araç (Python/GhostScript) Yerine Saf Node.js (WebAssembly) Seçildi?
Bilgisayarda Python ve C++ derleme araçlarının yolları bozuk olduğu için, bu tür bağımlılıkları sıfırdan kurmaya çalışmak Windows sisteminde hem çok fazla vakit alacaktı hem de sistemin geneli için kirli bir kuruluma yol açacaktı. Bu sebeple **%100 saf JavaScript ve WebAssembly (WASM)** kullanan kütüphaneler seçildi.

- **`mupdf`**: PDF sayfalarını direkt hafızada (RAM) yüksek çözünürlüklü resimlere (`Uint8Array`) çevirebilen, hiçbir ekstra Windows programı istemeden hızlı çalışan çok güçlü bir kütüphane kullanıldı.
- **`tesseract.js`**: `mupdf` ile çıkarılan resim karelerini alıp resimde Türkçe yazan karakterleri okuyan yapay zeka/OCR aracı kullanıldı.

## Sonuç
`temp_pdf_parser/pdf_ocr.mjs` isimli kod yazıldı. Bu kod, 6 hatalı PDF dosyasındaki tüm sayfaları teker teker fotoğrafa çevirdi, Türkçe dil motoruyla tarattı ve metinleri çıkardı. 

Elde edilen veriler okunabilir bir `.txt` verisi olarak projeye dâhil edilerek RAG veri setindeki "bilgi eksikliği" ve "belge okuyamama" problemi tamamen ve kalıcı olarak giderilmiştir.
