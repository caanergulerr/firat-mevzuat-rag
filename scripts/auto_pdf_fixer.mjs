import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pdfParse = require('pdf-parse');
import { createWorker } from 'tesseract.js';
import * as mupdf from 'mupdf';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pdfDir = path.join(__dirname, '..', 'data', 'raw');
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
            // 1. ADIM: Belgenin sağlıklı olup olmadığını ölç (Metin yoğunluğunu ve bozuk Font Encoding'i kontrol et)
            // Performans için sadece ilk 3 sayfaya bakılır.
            const parsed = await pdfParse(dataBuffer, { max: 3 });
            const rawText = parsed.text || '';
            const textL = rawText.trim().replace(/\s+/g, '');
            const lowerText = rawText.toLowerCase();

            // Sık görülen Font Encoding bozulmaları (Ç-> , Ö-> , Ş-> )
            const isCorrupted = lowerText.includes('ift anadal') || 
                                lowerText.includes('renci') || 
                                lowerText.includes('bavuru') || 
                                lowerText.includes('artlar');

            if (textL.length >= 50 && !isCorrupted) {
                // Bu dosya %100 sağlıklı ve okunabilir metin katmanına sahip. RAG için hazır.
                // console.log(`[PAS GEÇİLDİ] ${file} - Yeterli temiz metin var.`);
                continue;
            }

            console.log(`\n⚠️ [GÖRSEL VEYA BOZUK FONT TESPİT EDİLDİ]: ${file}`);
            if (isCorrupted) {
                console.log(`    >> HATA: Metin var ama Türkçe karakterler (Ç,Ö,Ş) bozuk kodlanmış! Oto-Tamir (OCR) başlatılıyor...`);
            } else {
                console.log(`    >> Belge okunmaya uygun değil (Görsel). Oto-Tamir (OCR) operasyonu başlatılıyor...`);
            }

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

            // 3. ADIM: Okunan temiz metni .txt dosyası olarak kaydet (PDF yazma — kısır döngüyü önler)
            process.stdout.write(`    >> Temiz metin .txt olarak kaydediliyor... `);
            const txtPath = filePath + '.txt';
            fs.writeFileSync(txtPath, fullText.trim(), { encoding: 'utf8' });
            
            console.log(`    ✅ BAŞARILI: ${file}.txt oluşturuldu ve RAG için %100 hazır!`);

            fixedCount++;

        } catch (err) {
            console.error(`    ❌ [KRİTİK HATA] ${file} tamir edilirken çöktü:`, err.message);
        }
    }

    if (worker) await worker.terminate();
    
    console.log("----------------------------------------------------------------------------------");
    if (fixedCount > 0) {
        console.log(`🎉 OTO-TAMİR TAMAMLANDI! Toplam ${fixedCount} adet bozuk PDF için .txt dosyası üretildi.`);
    } else {
        console.log(`✅ KONTROL TAMAMLANDI! Tüm belgeleriniz zaten temiz, bozuk belge bulunamadı.`);
    }
}

processPdfs();
