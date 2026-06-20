const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

const pdfDir = path.join(__dirname, '..', 'yönetmelikler');
const files = fs.readdirSync(pdfDir).filter(f => f.toLowerCase().endsWith('.pdf'));

console.log(`Toplam ${files.length} PDF bulundu. Analiz ediliyor (bu işlem biraz zaman alabilir)...\n`);

let hasTextCount = 0;
let noTextCount = 0;
let errorCount = 0;

let hasTextFiles = [];
let noTextFiles = [];

async function scanPdfs() {
    for (const file of files) {
        const filePath = path.join(pdfDir, file);
        const dataBuffer = fs.readFileSync(filePath);

        try {
            // Sadece ilk birkaç sayfaya bakmak performans için daha iyi olabilir ama
            // metnin olup olmadığından emin olmak için parse ediyoruz.
            // pdf-parse ile tüm döküman parse edilir.
            const data = await pdf(dataBuffer, { max: 3 }); // İlk 3 sayfaya bakmak genelde yeterlidir.
            
            let text = data.text ? data.text.trim().replace(/\s+/g, '') : '';
            
            if (text.length > 50) {
                hasTextCount++;
                hasTextFiles.push({ file, pages: data.numpages, charCount: text.length });
            } else {
                noTextCount++;
                noTextFiles.push({ file, pages: data.numpages, charCount: text.length });
            }
        } catch (err) {
            errorCount++;
            console.error(`[HATA] ${file}: ${err.message}`);
        }
    }

    console.log(`\n======== SONUÇLAR ========`);
    console.log(`✅ METİN İÇERENLER: ${hasTextCount} adet`);
    console.log(`❌ METİN İÇERMEYENLER (Sadece görsel / Boş): ${noTextCount} adet`);
    if (errorCount > 0) console.log(`⚠️ OKUNAMAYAN / HATA VEREN: ${errorCount} adet`);

    if (noTextCount > 0) {
        console.log(`\n--- METİN İÇERMEYEN PDFLER ---`);
        noTextFiles.forEach(f => {
            console.log(`- ${f.file} (${f.pages} sayfa, ~${f.charCount} karakter)`);
        });
    }

    /*
    if (hasTextCount > 0) {
        console.log(`\n--- BAZI METİNLİ PDFLER ---`);
        hasTextFiles.slice(0, 5).forEach(f => {
            console.log(`- ${f.file} (${f.pages} sayfa, ~${f.charCount} karakter)`);
        });
    }
    */
}

scanPdfs();
