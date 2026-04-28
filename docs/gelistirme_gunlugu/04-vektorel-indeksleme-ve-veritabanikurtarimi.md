# Geliştirme: Vektörel İndeksleme ve Veritabanı/Git Kurtarma
**Tarih:** 01-02 Nisan 2026
**Efor:** Orta
**Durum:** Tamamlandı

## 1. RAG için Metin Parçalama (Chunking) & ChromaDB Geçişi
RAG sisteminin makine tarafına asıl zekayı verebilmek amacıyla **Data Chunking (Veri Parçalama)** ve **ChromaDB Vektörel Veritabanı** indekslemesi hayata geçirildi. 
- Belgelerden OCR ve diğer yollarla alınan metinler büyük yığınlar halinde LLM (Large Language Model) içerisine gönderilmek yerine anlamsal limitler dahilinde "chunk"lara (parçalara) bölündü.
- Bu veriler başarılı bir şekilde sisteme işlenerek, boyutları sebebiyle git kılıfına sığması sorununu engellemek amacıyla doğrudan `.gitignore` özel ayarıyla repoya `data/processed/chunks.json` adında sabitlendi. İstendiğinde ChromaDB vasıtasıyla belgelerin anlamsal aramaları yapılabilecek duruma geldi.

## 2. Repo Kurtarma ve Geçmiş Temizliği
Ekip içi geliştirme esnasında `data/raw/yönetmelikler/` içerisinde yer alan tam **143 adet PDF dosyası** yanlış PR/Merge işlemleri sonucu silinerek projeden uçuruldu.
- **Veri Kurtarma:** Repository geçmişine (commit history) dönülerek silinmiş olan tüm bu veriler eksiksiz bir şekilde eski halinden kurtarıldı ve projeye geri kazandırıldı.
- **Git Temizliği:** Diğer takım arkadaşlarının projeye tam adapte olabilmesi için atılmış İngilizce commit mesajları sonradan müdahale ile **anadilde yapılandırılıp** ("özellik: ... eklendi", "düzenleme: ...") Force Push ile GitHub üzerindeki repo sıfırdan revize edildi.
- Kafa karıştırıcı duran `BURAYA_PDF_KOYUN.txt` dosyası sistemden tamamen kaldırılarak daha temiz bir dosya ağacına ulaşıldı.
