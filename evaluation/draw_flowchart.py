"""
Firat Mevzuat RAG — Temiz Akis Semasi v3
Genis tuval, hicbir kesisme ve kesinti yok
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─────────────────────────────────────────
# TUVAL  (genis, yuksek)
# ─────────────────────────────────────────
W, H = 16, 28          # genislik, yukseklik (birim)
fig, ax = plt.subplots(figsize=(W*0.9, H*0.9))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
fig.patch.set_facecolor('#FAFAFA')
CX = W / 2             # merkez x = 8.0

# ─────────────────────────────────────────
# RENKLER
# ─────────────────────────────────────────
C = dict(
    mavi    = '#1565C0',
    mor     = '#6A1B9A',
    mor2    = '#7B1FA2',
    mor3    = '#AB47BC',
    koyu_mor= '#4A148C',
    gri     = '#37474F',
    turuncu = '#E65100',
    sari    = '#F9A825',
    cam     = '#00695C',
    yesil   = '#2E7D32',
    koyu_y  = '#1B5E20',
    kirmizi = '#C62828',
    acik_g  = '#ECEFF1',
)
W_TXT = 'white'

# ─────────────────────────────────────────
# YARDIMCI FONKSIYONLAR
# ─────────────────────────────────────────
def kutu(cx, cy, w, h, satir1, satir2='', renk='#333', fs1=12, fs2=9.5, radius=0.25):
    x0, y0 = cx - w/2, cy - h/2
    ax.add_patch(mpatches.FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=f"round,pad=0.1,rounding_size={radius}",
        facecolor=renk, edgecolor='white', linewidth=2.0, zorder=3,
        clip_on=False))
    if satir2:
        ax.text(cx, cy + h*0.17, satir1, ha='center', va='center',
                fontsize=fs1, color=W_TXT, fontweight='bold', zorder=4, clip_on=False)
        ax.text(cx, cy - h*0.22, satir2, ha='center', va='center',
                fontsize=fs2, color=W_TXT, alpha=0.9, zorder=4, clip_on=False)
    else:
        ax.text(cx, cy, satir1, ha='center', va='center',
                fontsize=fs1, color=W_TXT, fontweight='bold', zorder=4, clip_on=False)


def elmas(cx, cy, w, h, satirlar, renk):
    pts = np.array([[cx, cy+h/2],[cx+w/2, cy],[cx, cy-h/2],[cx-w/2, cy]])
    ax.add_patch(plt.Polygon(pts, closed=True,
                 facecolor=renk, edgecolor='white', linewidth=2, zorder=3))
    lines = satirlar.split('\n')
    total = len(lines)
    for i, line in enumerate(lines):
        offset = (total - 1 - 2*i) * 0.18
        ax.text(cx, cy + offset, line, ha='center', va='center',
                fontsize=10.5, color=W_TXT, fontweight='bold', zorder=4)


def oval(cx, cy, w, h, yazi, renk, fs=12):
    ax.add_patch(mpatches.Ellipse(
        (cx, cy), w, h,
        facecolor=renk, edgecolor='white', linewidth=2.5, zorder=3))
    ax.text(cx, cy, yazi, ha='center', va='center',
            fontsize=fs, color=W_TXT, fontweight='bold', zorder=4)


def ok(x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#546E7A', lw=2.3), zorder=2)


def cizgi(x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color='#546E7A', lw=2.3, zorder=2)

# ─────────────────────────────────────────────────────────
# BASLIK
# ─────────────────────────────────────────────────────────
ax.text(CX, 27.5, 'Firat Universitesi Mevzuat RAG Sistemi',
        ha='center', va='center', fontsize=20, fontweight='bold', color='#1A237E')
ax.text(CX, 26.9, 'Calisma Akisi Semasi',
        ha='center', va='center', fontsize=12, color='#546E7A')

# ─────────────────────────────────────────────────────────
# [0] BASLANGIC OVAL
# ─────────────────────────────────────────────────────────
oval(CX, 26.1, 6, 0.7, 'Ogrenci Soruyu Yazar', C['mavi'])
ax.text(CX + 4.2, 26.1, '"Ustten ders alabilir miyim?"',
        ha='left', va='center', fontsize=10, color='#546E7A', fontstyle='italic')
ok(CX, 25.75, CX, 25.25)

# ─────────────────────────────────────────────────────────
# [1] ADIM 1 BASLIK — SORGU GENISLETME
# ─────────────────────────────────────────────────────────
kutu(CX, 24.85, 12, 0.72, 'ADIM 1 — SORGU GENISLETME  (Query Expansion)',
     '', C['mor'], fs1=13)
ok(CX, 24.49, CX, 23.95)

# [1a] Sol kutu — Statik Sozluk
kutu(4.0, 23.2, 6.0, 1.5,
     'YONTEM A: Statik Sozluk',
     'Kod icine yazili kelime listesi\n"ustten ders" -> "ust yariyil GNO 3.00"\nHizli / Internet gerekmez',
     C['mor2'], fs1=11, fs2=9)

# "VEYA" etiketi
ax.text(CX, 23.2, 'VEYA', ha='center', va='center',
        fontsize=14, color=C['mor'], fontweight='bold')

# [1b] Sag kutu — Gemini API
kutu(12.0, 23.2, 6.0, 1.5,
     'YONTEM B: Gemini API  (Yedek)',
     'Listede olmayan sorular icin\nYapay zekaya genislettirilir\nDaha yavas / Internet gerekir',
     C['mor3'], fs1=11, fs2=9)

# Sol alt + Sag alt -> birlestir ortada
cizgi(4.0, 22.45, 4.0, 22.1)
cizgi(12.0, 22.45, 12.0, 22.1)
cizgi(4.0, 22.1, 12.0, 22.1)
ok(CX, 22.1, CX, 21.65)

# Birlesim kutusu
kutu(CX, 21.25, 11, 0.65,
     'Genisletilmis Sorgu olusturuldu',
     '"ustten ders" + "ust yariyil GNO 3.00 art sart"',
     C['koyu_mor'], fs1=11, fs2=9.5)
ok(CX, 20.92, CX, 20.42)

# ─────────────────────────────────────────────────────────
# [2] ADIM 2 BASLIK — HIBRIT ARAMA
# ─────────────────────────────────────────────────────────
kutu(CX, 20.05, 12, 0.65, 'ADIM 2 — HIBRIT ARAMA  (Hybrid Retrieval)',
     '', C['gri'], fs1=13)
ok(CX, 19.72, CX, 19.15)

# [2a] Sol kutu — BM25
kutu(4.5, 18.35, 6.5, 1.4,
     'BM25  (Kelime Eslestirme)',
     'Kelime kelime arar — rank-bm25\n"Google gibi" tam kelime aramasi\nHizli ve guvenilir',
     C['sari'], fs1=11.5, fs2=9.5)

# "+" etiketi
ax.text(CX, 18.35, '+', ha='center', va='center',
        fontsize=22, color=C['gri'], fontweight='bold')

# [2b] Sag kutu — Semantik
kutu(11.5, 18.35, 6.5, 1.4,
     'Semantik Arama  (Anlam Eslestirme)',
     'Anlami karsilastirir — ChromaDB\n"ChatGPT gibi" anlam anar\nBERTurk embedding modeli',
     C['cam'], fs1=11.5, fs2=9.5)

# Birlestir
cizgi(4.5, 17.65, 4.5, 17.3)
cizgi(11.5, 17.65, 11.5, 17.3)
cizgi(4.5, 17.3, 11.5, 17.3)
ok(CX, 17.3, CX, 16.85)

# [2c] RRF Fuzyonu
kutu(CX, 16.45, 11, 0.72,
     'RRF Fuzyonu — Sonuclari Birlestir',
     '%60 Semantik + %40 BM25  ->  En alakali 15 madde secilir',
     C['yesil'], fs1=11.5, fs2=9.5)
ok(CX, 16.09, CX, 15.5)

# ─────────────────────────────────────────────────────────
# [3] KARAR ELEMASI
# ─────────────────────────────────────────────────────────
elmas(CX, 14.75, 6, 1.25,
      'Yeterli madde\nbulundu mu?\n(Skor >= 0.1)',
      C['turuncu'])

# EVET — asagi
ok(CX, 14.12, CX, 13.5)
ax.text(CX + 0.2, 13.85, 'EVET', ha='left', va='center',
        fontsize=11, color=C['yesil'], fontweight='bold')

# HAYIR — saga (daha guvende)
cizgi(11.0, 14.75, 13.5, 14.75)
ax.text(12.1, 14.95, 'HAYIR', ha='center', va='bottom',
        fontsize=11, color=C['kirmizi'], fontweight='bold')
kutu(13.5, 14.75, 3.5, 1.2,
     '"Bilgi bulunamadi"',
     'yaniti kullaniciya doner',
     C['kirmizi'], fs1=11, fs2=9)

# HAYIR kutusundan asagi cikip evet yoluna birlestir
cizgi(13.5, 14.15, 13.5, 12.4)
cizgi(9.0, 12.4, 13.5, 12.4)
ok(9.0, 12.4, 9.0, 12.05)   # sadece gosterim — cevap cikis kutusuna birlestir
# Asil cizgiyi evet yoluna birlestir
cizgi(CX, 12.4, 9.0, 12.4)

# ─────────────────────────────────────────────────────────
# [4] ADIM 3 — CEVAP URETIMI
# ─────────────────────────────────────────────────────────
kutu(CX, 13.1, 12, 0.65, 'ADIM 3 — CEVAP URETIMI  (Generation)',
     '', C['gri'], fs1=13)
ok(CX, 12.77, CX, 12.25)

# [4a] Sol — Sistem Prompt
kutu(5.0, 11.55, 6.5, 1.2,
     'Sistem Komutu  (Prompt)',
     'Rol + Kurallar\nKaynak gosterme zorunlulugu',
     '#388E3C', fs1=11, fs2=9.5)

ax.text(CX, 11.55, '+', ha='center', va='center',
        fontsize=20, color=C['gri'], fontweight='bold')

# [4b] Sag — Gemini
kutu(11.0, 11.55, 6.5, 1.2,
     'Gemini 2.5-flash  (LLM)',
     'Maddelerden Turkce cevap uretir\nBuyuk dil modeli',
     C['koyu_y'], fs1=11, fs2=9.5)

# Birlestir
cizgi(5.0, 10.95, 5.0, 10.65)
cizgi(11.0, 10.95, 11.0, 10.65)
cizgi(5.0, 10.65, 11.0, 10.65)
ok(CX, 10.65, CX, 10.2)

# ─────────────────────────────────────────────────────────
# [5] CIKIS KUTUSU
# ─────────────────────────────────────────────────────────
kutu(CX, 9.8, 11, 0.72,
     'Kaynakli Turkce Cevap  +  Madde Referansi',
     'ornek: "GNO en az 3.00 olmali  —  Kaynak: Lisans Yonetmeligi, Madde 11"',
     C['yesil'], fs1=11.5, fs2=9.5)
ok(CX, 9.44, CX, 8.95)

# HAYIR yolu buraya da gelsin
ok(9.0, 12.05, 9.0, 9.44)

# ─────────────────────────────────────────────────────────
# [6] BITIS OVAL
# ─────────────────────────────────────────────────────────
oval(CX, 8.65, 7, 0.68, 'Ogrenciye Yanit Doner', C['mavi'])

# ─────────────────────────────────────────────────────────
# AYIRICI CIZGI
# ─────────────────────────────────────────────────────────
ax.axhline(y=8.0, xmin=0.02, xmax=0.98,
           color='#B0BEC5', lw=1.2, linestyle='--')

# ─────────────────────────────────────────────────────────
# LEGEND
# ─────────────────────────────────────────────────────────
ax.text(0.6, 7.65, 'Kullanilan Yontemler:', fontsize=12,
        color='#37474F', fontweight='bold', va='top')

legend = [
    (C['mor'],    'Query Expansion — Sorgu Genisletme (Statik Sozluk + Gemini yedek)'),
    (C['sari'],   'BM25 — Anahtar Kelime Aramasi (TF-IDF tabanli)'),
    (C['cam'],    'Semantik Arama — Anlam Vektoru (BERTurk + ChromaDB)'),
    (C['yesil'],  'RRF — Hibrit Siralamayi Birlestirme'),
    (C['koyu_y'], 'RAG Generation — Gemini 2.5-flash ile Turkce Cevap Uretme'),
]
for i, (renk, etiket) in enumerate(legend):
    y = 7.15 - i * 0.52
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.6, y - 0.14), 1.2, 0.32,
        boxstyle="round,pad=0.05",
        facecolor=renk, edgecolor='white', linewidth=1, zorder=3))
    ax.text(2.1, y + 0.02, etiket, ha='left', va='center',
            fontsize=10, color='#212121')

# ─────────────────────────────────────────────────────────
# METRIK KUTULARI
# ─────────────────────────────────────────────────────────
metrikler = [
    ('143 PDF Belge',         0.6),
    ('2.815 Madde',           5.7),
    ('3.274 Parca (Chunk)',   10.8),
    ('Yanit Suresi: ~6-8 sn', 0.6),
    ('Top-K: 15  |  Esik: 0.1', 5.7),
    ('RRF: %60 Sem + %40 BM25', 10.8),
]
for i, (metin, x0) in enumerate(metrikler):
    row = i // 3
    y0 = 4.35 - row * 0.68
    ax.add_patch(mpatches.FancyBboxPatch(
        (x0, y0 - 0.22), 4.6, 0.44,
        boxstyle="round,pad=0.07",
        facecolor=C['acik_g'], edgecolor='#CFD8DC', linewidth=1, zorder=3))
    ax.text(x0 + 2.3, y0, metin, ha='center', va='center',
            fontsize=10, color='#37474F', fontweight='bold')

# ─────────────────────────────────────────────────────────
# KAYDET
# ─────────────────────────────────────────────────────────
plt.tight_layout(pad=0.4)
plt.savefig('evaluation/akis_semasi.png', dpi=150,
            bbox_inches='tight', facecolor='#FAFAFA')
print('Sema kaydedildi -> evaluation/akis_semasi.png')
plt.close()
