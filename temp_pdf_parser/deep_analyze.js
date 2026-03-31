const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

const folderPath = path.join(__dirname, '../yönetmelikler');
// Load files, ignore deleted ones if they are gone (by catching fs error or just readdir)
const files = fs.readdirSync(folderPath).filter(f => f.toLowerCase().endsWith('.pdf'));

async function analyze() {
  const parsedDocs = [];
  console.log(`Analyzing ${files.length} pdfs...`);

  for (const file of files) {
    const filePath = path.join(folderPath, file);
    try {
      const dataBuffer = fs.readFileSync(filePath);
      const data = await pdf(dataBuffer);
      
      // Get the full text, remove ALL non-alphanumeric (except Turkish characters) to ensure strict content matching
      let rawText = data.text || '';
      let cleanText = rawText.toUpperCase().replace(/[^A-ZÇĞIİÖŞÜ0-9]/g, '');
      
      parsedDocs.push({ 
          file, 
          textLength: cleanText.length, 
          cleanText: cleanText,
          rawStart: rawText.replace(/\s+/g, ' ').substring(0, 100)
      });
    } catch (e) {
      console.error(`Error parsing ${file}`);
    }
  }

  // 1. Find Exact Text Matches (Length & Content Match)
  // Even if size differs due to metadata/compression, the text will be 100% identical
  const exactGroups = {};
  for (const doc of parsedDocs) {
      if (doc.textLength === 0) continue; // Skip unparsable or image-only ones
      
      const hashKey = doc.cleanText; 
      if (!exactGroups[hashKey]) {
          exactGroups[hashKey] = [];
      }
      exactGroups[hashKey].push(doc);
  }

  console.log('\n=== BİREBİR AYNI METNE SAHİP DOSYALAR (Tüm Metin Uyuşanlar) ===');
  let foundExact = false;
  for (const key in exactGroups) {
      if (exactGroups[key].length > 1) {
          foundExact = true;
          let names = exactGroups[key].map(d => d.file).join(', ');
          console.log(`- ${names}`);
          console.log(`  (İçerik Başlangıcı: "${exactGroups[key][0].rawStart.trim()}...")\n`);
      }
  }
  if (!foundExact) console.log('Bulunamadı.\n');

  // 2. Find Very Similar Lengths (could be 1-2 word difference)
  console.log('=== YÜKSEK BENZERLİK GÖSTERENLER (Metin Uzunluğu +/- %2 Aynı Olanlar) ===');
  const sorted = [...parsedDocs].filter(d => d.textLength > 100).sort((a,b) => a.textLength - b.textLength);
  let checkedPairs = new Set();
  
  for (let i = 0; i < sorted.length; i++) {
      for (let j = i + 1; j < Math.min(i + 5, sorted.length); j++) { // Check next 4 closest lengths
          const docA = sorted[i];
          const docB = sorted[j];
          
          if (docA.textLength === docB.textLength && docA.cleanText === docB.cleanText) {
              continue; // Already printed above
          }
          
          const diff = Math.abs(docA.textLength - docB.textLength);
          const ratio = diff / docA.textLength;
          
          if (ratio < 0.02) { // Less than 2% difference
              // Quick similarity check (overlap in first 500 chars)
             let startA = docA.cleanText.substring(0, 500);
             let startB = docB.cleanText.substring(0, 500);
             if (startA === startB) {
                 const pairKey = [docA.file, docB.file].sort().join('-');
                 if (!checkedPairs.has(pairKey)) {
                     checkedPairs.add(pairKey);
                     console.log(`- ${docA.file} (${docA.textLength} harf) ve ${docB.file} (${docB.textLength} harf)`);
                     console.log(`  (Muhtemel ufak revizyon farkı. Orijinal başlık: "${docA.rawStart.trim()}...")\n`);
                 }
             }
          }
      }
  }

  // 3. Find Unparsable (Image/Scanned)
  const unparsable = parsedDocs.filter(d => d.textLength < 50); // Less than 50 chars is suspicious
  if (unparsable.length > 0) {
      console.log('=== METNİ OKUNAMAYANLAR (Tarayıcı Görüntüsü veya Korumalı PDF) ===');
      console.log('Dosyalar: ' + unparsable.map(d => d.file).join(', '));
      // Explaining why we couldn't parse these
      console.log('NOT: Bu dosyalar PDF okuyucular içindeki salt görsel taramalardan ibaret olabilir, veya standart dışı bir font kodlaması (CIDToUnicode hatası) yüzünden bilgisayar metni göremiyor olabilir.\n');
  }
}

analyze();
