const fs = require('fs');
const path = require('path');
const PDFDocument = require('pdfkit');

const outDir = path.join(__dirname, '..', 'yönetmelikler', 'OCR_Ciktilari');
const arialFontPath = 'C:\\Windows\\Fonts\\arial.ttf'; // Windows'un orijinal Arial fontu (Türkçe %100 uyumlu)

async function convertTxtToPdf() {
    try {
        const files = fs.readdirSync(outDir).filter(f => f.endsWith('_ocr.txt'));
        console.log(`\nToplam ${files.length} adet metin dosyası şık bir PDF formatına çevriliyor...`);

        for (const file of files) {
            const txtPath = path.join(outDir, file);
            // Örneğin: 1644309301_ocr.txt -> 1644309301_okunabilir.pdf
            const pdfPath = path.join(outDir, file.replace('_ocr.txt', '_okunabilir.pdf'));
            const textContent = fs.readFileSync(txtPath, 'utf8');

            const doc = new PDFDocument({
                margin: 50,
                info: {
                    Title: `Temizlenmiş - ${file.replace('_ocr.txt', '')}`,
                    Author: 'Fırat Mevzuat RAG (AI)',
                }
            });
            
            doc.pipe(fs.createWriteStream(pdfPath));

            // Başlık
            doc.font(arialFontPath)
               .fontSize(16)
               .text(`Dönüştürülen Metin: ${file.replace('_ocr.txt', '').toUpperCase()}`, { align: 'center' });
               
            doc.moveDown(1.5);

            // Ana Metin
            doc.fontSize(11)
               .lineGap(4)
               .text(textContent, {
                   align: 'justify' // metni iki yana yaslar
               });

            doc.end();
            console.log(`✅ Oluşturuldu: ${path.basename(pdfPath)}`);
        }
        console.log("\n🏁 Tüm çeviriler tamamlandı! 'yönetmelikler/OCR_Ciktilari' klasörüne bakabilirsiniz.");
    } catch (err) {
        console.error("Dönüştürmede Hata:", err);
    }
}

convertTxtToPdf();
