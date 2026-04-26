import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pdfParse = require('pdf-parse');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const pdfDir = path.join(__dirname, '..', 'data', 'raw');

async function extractAll() {
    console.log("PDF'lerden metin çıkarma işlemi başlıyor (pdf-parse)...");
    const files = fs.readdirSync(pdfDir).filter(f => f.endsWith('.pdf'));
    
    let successCount = 0;
    
    for (const file of files) {
        const filePath = path.join(pdfDir, file);
        const txtPath = filePath + '.txt';
        
        try {
            const dataBuffer = fs.readFileSync(filePath);
            const data = await pdfParse(dataBuffer);
            
            // Eğer anlamlı bir Türkçe metin çıktıysa .txt olarak kaydet
            fs.writeFileSync(txtPath, data.text.trim(), { encoding: 'utf8' });
            successCount++;
            
        } catch (err) {
            console.error(`Hata (${file}):`, err.message);
        }
    }
    
    console.log(`✅ Toplam ${successCount} adet .pdf belgesinin tam metni çıkarıldı ve .txt olarak kaydedildi.`);
}

extractAll();
