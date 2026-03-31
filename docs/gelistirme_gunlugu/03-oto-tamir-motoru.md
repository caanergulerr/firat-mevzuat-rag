# Geliştirme: Otomatik PDF Tamir Motoru (Auto Fixer)
**Tarih:** 31 Mart 2026
**Efor:** Yüksek
**Durum:** Tamamlandı

## Yapılan İşlem ve Nedenleri
İlk iki kayıtta bahsettiğimiz gibi, taranmış fotoğraflı PDF'lere manuel olarak müdahale edebilmiştik. Ancak ilerleyen aylarda RAG sistemine **yeni eklenecek olan taranmış PDF'lerin de** otomatik olarak OCR ile okunabilir metne dönüştürülmesi gerekiyordu. Aksi halde sistem, insan müdahalesi olmadan çalışamaz hale gelirdi. 

Bu sorunu çözmek için `scripts/auto_pdf_fixer.mjs` isimli yeni bir "Veri Temizlik ve Tamir Motoru" projenin ana mimarisine eklendi.

## Sistem Nasıl Çalışıyor?
1. `pdf-parse` eklentisi kullanılarak belgenin içinde en az 50 harf (okunabilir bir katman) olup olmadığı kontrol ediliyor.
2. Eğer dosyanın içi yazıyla doluysa sistem hiçbir OCR yüküne/işlemci kaybına girmeden o dosyayı es geçiyor.
3. Eğer dosyanın içinde yazı yoksa veya fotoğraf şeklindeyse sistem durumu algılayıp anında `tesseract.js` OCR motorunu uyandırıyor.
4. Resimdeki yazılar okunarak yeni nesil, aranabilir (100% Türkçe destekli Helvetica/Arial fontlarıyla) bir PDF'e dönüştürülüyor ve eski dosya silinip onun yerine geçiriliyor.

## Python Sorunu Giderildi
Buna ek olarak geliştirici makinesindeki asıl sorun olan "Python Çalışmama" kliği kırılmış ve bilgisayara `winget` üzerinden sessizce **Python 3.11** versiyonu yüklenerek RAG altyapısının asıl ML (Makine Öğrenimi) kurulumlarına başlama zemini hazırlanmıştır.
