import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pdfParse = require('pdf-parse');
import { createWorker } from 'tesseract.js';
import * as mupdf from 'mupdf';
import PDFDocument from 'pdfkit';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pdfDir = path.join(__dirname, '..', 'yönetmelikler');
const arialFontPath = 'C:\\Windows\\Fonts\\arial.ttf';

async function processPdfs() {
    const files = fs.readdirSync(pdfDir).filter(f => f.endsWith('.pdf'));
    console.log(`\n🤖 Otomatik Veri Temizlik (Oto-Tamir) Motoru Başlatıldı: Toplam ${files.length} belge kontrol edilecek...`);
    console.log("----------------------------------------------------------------------------------");

    let worker = null; // OCR motoru (Sadece ihtiyaç olursa arka planda indirilir/başlatılır)
    let fixedCount = 0;

    for (const file of files) {
        const filePath = path.join(pdfDir, file);
        const dataBuffer = fs.readFileSync(filePath);

        try {
            // 1. ADIM: Belgenin sağlıklı olup olmadığını ölç (Metin yoğunluğunu kontrol et)
            // Performans için sadece ilk 3 sayfaya bakılır.
            const parsed = await pdfParse(dataBuffer, { max: 3 });
            const text = parsed.text ? parsed.text.trim().replace(/\s+/g, '') : '';

            if (text.length >= 50) {
                // Bu dosya %100 sağlıklı ve okunabilir metin katmanına sahip. RAG için hazır.
                // Log kalabalığı yapmamak için sessizce (veya kısaca) geçiyoruz.
                // console.log(`[PAS GEÇİLDİ] ${file} - Yeterli metin var.`);
                continue;
            }

            console.log(`\n⚠️ [GÖRSEL/TARAMA BELGE TESPİT EDİLDİ]: ${file}`);
            console.log(`    >> Belge okunmaya uygun değil. Oto-Tamir (OCR) operasyonu başlatılıyor...`);

            // Eğer Tesseract motoru henüz ayağa kalkmadıysa başlat
            if (!worker) worker = await createWorker('tur');

            // 2. ADIM: MuPDF ile görseli çıkar, OCR ile oku
            const doc = mupdf.Document.openDocument(dataBuffer, "application/pdf");
            const pageCount = doc.countPages();
            let fullText = "";

            for (let i = 0; i < pageCount; i++) {
                process.stdout.write(`    >> Sayfa ${i + 1}/${pageCount} fotoğraflanıyor ve yapay zeka ile okunuyor... `);
                
                const page = doc.loadPage(i);
                const pixmap = page.toPixmap(mupdf.Matrix.scale(2, 2), mupdf.ColorSpace.DeviceRGB, false);
                const pngBuffer = Buffer.from(pixmap.asPNG());
                
                const { data: { text: pageText } } = await worker.recognize(pngBuffer);
                fullText += `\n${pageText}\n`;
                
                process.stdout.write("Bitti!\n");
            }

            // 3. ADIM: Okunan verileri güzel formatlı yeni bir PDF içine yaz
            process.stdout.write(`    >> Temiz metin yeni PDF dosyasına yazılıyor... `);
            const tempPdfPath = path.join(pdfDir, file + '.temp');
            const pdfDoc = new PDFDocument({ margin: 50, info: { Title: 'Tamir Edilmiş Belge - Fırat Mevzuat AI' } });
            
            const writeStream = fs.createWriteStream(tempPdfPath);
            pdfDoc.pipe(writeStream);

            // Windows Arial fontu ile (Türkçe 100% uyumlu)
            pdfDoc.font(arialFontPath)
                  .fontSize(11)
                  .lineGap(4)
                  .text(fullText.trim(), { align: 'justify' });

            pdfDoc.end();

            // Kayıt bitmesini bekle
            await new Promise((resolve) => writeStream.on('finish', resolve));
            
            // 4. ADIM: Eski bozuk belgeyi sistemden sil ve yerine yenisini koy
            fs.unlinkSync(filePath);             // Eskisini sil
            fs.renameSync(tempPdfPath, filePath); // Yenisini asıl isme çevir
            
            console.log(`    ✅ OPARASYON BAŞARILI: ${file} eskisinin yerine kaydedildi ve okumaya/RAG işlemine %100 hazır!`);
            fixedCount++;

        } catch (err) {
            console.error(`    ❌ [KRİTİK HATA] ${file} tamir edilirken çöktü:`, err.message);
        }
    }

    if (worker) await worker.terminate();
    
    console.log("----------------------------------------------------------------------------------");
    if (fixedCount > 0) {
        console.log(`🎉 OTO-TAMİR TAMAMLANDI! Toplam ${fixedCount} adet bozuk/okunamayan PDF başarıyla tamir edildi.`);
    } else {
        console.log(`✅ KONTROL TAMAMLANDI! Tüm belgeleriniz zaten okumaya uygun, bozuk belge bulunamadı.`);
    }
}

processPdfs();
