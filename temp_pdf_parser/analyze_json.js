const fs = require('fs');

const data = JSON.parse(fs.readFileSync('output.json'));

let ciftAnadalS = data.filter(d => d.isCiftAnadal);
console.log('=== Çift Anadal İçeren / İlgili Dosyalar ===');
ciftAnadalS.forEach(d => console.log(`- ${d.file} (\n   Özet: ${d.snippet.substring(0, 150)}...\n  )`));

console.log('\n=== Muhtemel Kopya Dosyalar (İçerik Benzerliği) ===');
// Clean up snippets and group the first 100 characters ignoring punctuation/spaces
const groups = {};
data.forEach(d => {
    let cleanText = d.snippet.replace(/[^A-ZÇĞIİÖŞÜ0-9]/g, '');
    let key = cleanText.substring(0, 80);
    if (!groups[key]) groups[key] = [];
    groups[key].push(d);
});

let found = false;
for (const key in groups) {
    if (groups[key].length > 1) {
        found = true;
        console.log(`\nBenzeri Konu/Belge:`);
        console.log(`İlk kelimeler: "${groups[key][0].snippet.substring(0,100).replace(/\n/g, ' ')}..."`);
        console.log(`Dosyalar: ${groups[key].map(d=>d.file).join(', ')}`);
    }
}
if (!found) {
     console.log('Hiç kopya bulunamadı.');
}
