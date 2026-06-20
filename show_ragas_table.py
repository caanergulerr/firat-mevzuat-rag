import json
import pandas as pd

# Benchmark dataset'i yükle
with open('evaluation/benchmark_dataset.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# RAGAS metriklerinin açıklaması
ragas_info = {
    'Metrik': [
        'Faithfulness',
        'Answer Relevancy',
        'Context Precision',
        'Context Recall'
    ],
    'Açıklama': [
        'Cevabın bağlamda verilen bilgilere sadık kalma oranı',
        'Cevabın soruya ne kadar uygun olduğu',
        'Alınan bağlamın ne kadarının uygun olduğu',
        'Alınan bağlamın uygun olanların ne kadarını bulduğu'
    ],
    'Aralık': ['0.0 - 1.0'] * 4
}

print('\n' + '='*80)
print('RAGAS DEĞERLENDİRME METRİKLERİ')
print('='*80)
print(pd.DataFrame(ragas_info).to_string(index=False))

print('\n\n' + '='*80)
print('BENCHMARK DATASET ÖZETİ')
print('='*80)
print(f'Toplam Sorular: {len(data)}')
print(f'\nSorular:')
for i, item in enumerate(data[:5], 1):
    print(f'  {i}. {item["question"]}')
if len(data) > 5:
    print(f'  ... ve {len(data)-5} soru daha')

print('\n' + '='*80)
print('RAGAS SONUÇLARI TABLOSU FORMATI (ÖRNEK)')
print('='*80)

# Örnek bir sonuçlar tablosu
sample_results = {
    'Soru': [data[i]['question'] for i in range(min(5, len(data)))],
    'Faithfulness': [0.85, 0.92, 0.78, 0.88, 0.81],
    'Answer Relevancy': [0.79, 0.85, 0.72, 0.80, 0.75],
    'Context Precision': [0.83, 0.90, 0.75, 0.86, 0.79],
    'Context Recall': [0.88, 0.95, 0.82, 0.91, 0.84]
}

df = pd.DataFrame(sample_results)
print('\nHer soru için RAGAS puanları:')
print(df.to_string(index=False))

print('\n\nOrtalama Skorlar:')
for col in ['Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall']:
    print(f'  {col}: {df[col].mean():.4f}')

print('\n' + '='*80)
