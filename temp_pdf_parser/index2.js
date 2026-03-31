const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');

const folderPath = path.join(__dirname, '../yönetmelikler');
const files = fs.readdirSync(folderPath).filter(f => f.toLowerCase().endsWith('.pdf'));

async function analyze() {
  const topics = [];
  console.log(`Analyzing ${files.length} pdfs...`);

  for (const file of files) {
    const filePath = path.join(folderPath, file);
    try {
      const dataBuffer = fs.readFileSync(filePath);
      const data = await pdf(dataBuffer);
      
      // Clean up text
      let text = data.text.trim().replace(/\s+/g, ' ');
      // get top 500 characters
      let snippet = text.substring(0, 500).toUpperCase();

      // Check if it's double major related to prioritize displaying it
      const isCiftAnadal = snippet.includes('ÇİFT') || snippet.includes('ANA DAL') || snippet.includes('ANADAL') || text.substring(0, 2000).toUpperCase().includes('ÇİFT ANADAL');
      
      topics.push({ file, snippet, isCiftAnadal });
    } catch (e) {
      //
    }
  }

  // To find similar PDFs heuristically, let's group by the first 15 alphanumeric characters (often "FIRAT ÜNİVERSİTE" etc.) + some title keywords
  // Better yet, just print all of them to a JSON file and I can read it.
  fs.writeFileSync('output.json', JSON.stringify(topics, null, 2));
  console.log('Saved to output.json');
}

analyze();
