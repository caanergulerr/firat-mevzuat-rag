const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

const folderPath = path.join(__dirname, '../yönetmelikler');
const files = fs.readdirSync(folderPath).filter(f => f.toLowerCase().endsWith('.pdf'));

async function analyze() {
  const topics = [];

  for (const file of files) {
    const filePath = path.join(folderPath, file);
    try {
      const dataBuffer = fs.readFileSync(filePath);
      // Wait to not exhaust memory simultaneously on all files
      const data = await pdf(dataBuffer);
      
      // Get the text, remove extra whitespace
      let text = data.text.trim().replace(/\s+/g, ' ');
      
      topics.push({ file, text: text });
    } catch (e) {
      // Ignore parse errors silently
    }
  }

  // Group by the first 60 alphanumeric characters
  const grouped = {};
  for (const item of topics) {
     const key = item.text.substring(0, 60).toLowerCase().replace(/[^a-z0-9ğüşıöç]/g, '');
     if (!grouped[key]) {
         grouped[key] = { preview: item.text.substring(0, 150), files: [] };
     }
     grouped[key].files.push(item.file);
  }

  console.log('=== AYNI KONUDAKI MUHTEMEL DOSYALAR ===');
  let dupCount = 0;
  for (const key in grouped) {
     if (grouped[key].files.length > 1) {
        console.log(`\nÖzet: "${grouped[key].preview}..."`);
        console.log(`Dosyalar:\n  - ${grouped[key].files.join('\n  - ')}`);
        dupCount++;
     }
  }
  
  if (dupCount === 0) {
      console.log("Aynı konuda duplicate pdf bulunamadı.");
  }
}

analyze();
