import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createWorker } from 'tesseract.js';
import * as mupdf from 'mupdf';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const pdfDir = path.join(__dirname, '..', 'yönetmelikler');
const outDir = path.join(__dirname, '..', 'yönetmelikler', 'OCR_Ciktilari');

if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
}

const targetPDFs = [
    '1644309301.pdf',
    '1687423214.pdf',
    '1687423276.pdf',
    '1729684211.pdf',
    '1736854229.pdf',
    '1762848869.pdf'
];

async function runOCR() {
    console.log("OCR İşlemi Başlatılıyor. (Bu işlem bilgisayar hızınıza göre biraz sürebilir...)\n");

    // Türkçe (tur) dil modeli otomatik indirilecek (tesseract.js tarafından bir kez yapılır)
    const worker = await createWorker('tur');

    for (const pdfName of targetPDFs) {
        const p = path.join(pdfDir, pdfName);
        if (!fs.existsSync(p)) {
            console.log(`[ATLANDI] ${pdfName} bulunamadı.`);
            continue;
        }

        console.log(`[İŞLENİYOR] ${pdfName}...`);
        
        try {
            // Dosyayı belleğe al
            const dataBuffer = fs.readFileSync(p);
            
            // MuPDF ile PDF'yi parse et (Native C++ kurulumu gerektirmeden çalışır)
            const doc = mupdf.Document.openDocument(dataBuffer, "application/pdf");
            const pageCount = doc.countPages();
            
            let fullText = "";

            // O pdf'teki her sayfa için OCR yap
            for (let i = 0; i < pageCount; i++) {
                console.log(`    -> Sayfa ${i + 1}/${pageCount} resme çevrilip okunuyor...`);
                
                const page = doc.loadPage(i);
                
                // OCR kalitesi için çözünürlüğü %200 yapıyoruz (2 katı büyütür)
                const scaleMatrix = mupdf.Matrix.scale(2, 2);
                
                // Sayfayı bir PNG verisine dönüştür (resim yap)
                const pixmap = page.toPixmap(scaleMatrix, mupdf.ColorSpace.DeviceRGB, false);
                const pngDataObj = pixmap.asPNG();
                
                // tesseract.js'e veriyi aktar
                const imgBuffer = Buffer.from(pngDataObj);
                const { data: { text } } = await worker.recognize(imgBuffer);
                fullText += `\n--- SAYFA ${i + 1} ---\n` + text + "\n";
                
                // Bellek yönetimi: MuPDF objelerini yok et
                // (Eğer bu sınıfların destroy methodu yoksa problem değil)
            }

            // Metni kaybetmeyelim
            const outPath = path.join(outDir, pdfName.replace('.pdf', '') + '_ocr.txt');
            fs.writeFileSync(outPath, fullText.trim(), 'utf8');
            console.log(`  ✅ Başarılı: ${pdfName} -> ${outPath}`);

        } catch (err) {
            console.error(`  ❌ Hata: ${pdfName} işlemi çöktü!`, err);
        }
    }

    await worker.terminate();
    console.log("\n🏁 TÜM OCR İŞLEMLERİ TAMAMLANDI!");
}

runOCR();
