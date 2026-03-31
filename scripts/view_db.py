import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "firat_mevzuat")

def view_db():
    print(f"ChromaDB klasörüne ({CHROMA_DB_PATH}) bağlanılıyor...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"Veritabanı koleksiyonu bulunamadı: {e}")
        return

    print(f"\n=> Veritabaninda Kayitli Toplam Vektor Sayisi: {collection.count()}")

    # Sadece ilk kaydı (peek=1) çek
    print("\n" + "="*50)
    print("           VERİTABANINDAN 1 ÖRNEK KAYIT")
    print("="*50)
    
    # peek fonksiyonu verileri listeler halinde döndürür
    peek_data = collection.peek(1)
    
    print("\n🔹 CHUNK ID:", peek_data["ids"][0])
    
    print("\n🔹 KAYITLI METİN (DOCUMENT):")
    print(peek_data["documents"][0])
    
    print("\n🔹 METADATALAR (ETİKETLER):")
    for key, val in peek_data["metadatas"][0].items():
        print(f"  - {key}: {val}")
        
    embedding = peek_data["embeddings"][0]
    print(f"\n🔹 VEKTÖR (SAYISAL) BOZUT BOYUTU: Tam {len(embedding)} farklı boyut (koordinat)")
    
    # Çok uzun olduğu için sadece ilk 10 ve son 2 sayıyı gösterelim
    print(f"🔹 İŞTE O SAYILAR (VEKTÖRLER):")
    print(f"  [{embedding[0]:.6f}, {embedding[1]:.6f}, {embedding[2]:.6f}, {embedding[3]:.6f}, " 
          f"{embedding[4]:.6f}, ... (toplam 768 sayı) ... "
          f"{embedding[-2]:.6f}, {embedding[-1]:.6f}]")

if __name__ == "__main__":
    view_db()
