import json
import os
import re
from pathlib import Path

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = name.replace('\n', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_unique_path(base_dir: Path, name: str, suffix: str) -> Path:
    base_name = name
    counter = 1
    new_path = base_dir / f"{base_name}{suffix}"
    while new_path.exists():
        new_path = base_dir / f"{base_name} ({counter}){suffix}"
        counter += 1
    return new_path

def main():
    map_path = Path('scripts/regulation_name_map.json')
    raw_dir = Path('data/raw')
    
    with open(map_path, 'r', encoding='utf-8') as f:
        name_map = json.load(f)
        
    new_map = {}
    renamed_count = 0
    
    for old_filename, actual_name in name_map.items():
        sanitized_name = sanitize_filename(actual_name)
        
        old_pdf_path = raw_dir / old_filename
        old_txt_path = raw_dir / (old_filename + ".txt")
        
        # Eğer PDF henüz değiştirilmediyse (halen varsa)
        if old_pdf_path.exists():
            new_pdf_path = get_unique_path(raw_dir, sanitized_name, '.pdf')
            try:
                print(f"Renaming {old_filename} -> {new_pdf_path.name}".encode('cp1254', errors='replace').decode('cp1254'))
            except Exception:
                pass
            os.rename(old_pdf_path, new_pdf_path)
            renamed_count += 1
            new_map[new_pdf_path.name] = actual_name
            
            # Txt dosyası varsa onu da aynı isimle adlandır
            if old_txt_path.exists():
                new_txt_path = raw_dir / (new_pdf_path.name + ".txt")
                os.rename(old_txt_path, new_txt_path)
        else:
            # Çoktan yeniden adlandırıldıysa
            # Eğer map_path.json da değişmişse map'e geri eklemeliyiz
            pass

    # Mevcut tüm PDF'leri kontrol edip map'e ekleyelim
    for f in raw_dir.glob('*.pdf'):
        if f.name not in new_map:
            # Map'te yoksa, isminden türet veya eski map'ten al
            new_map[f.name] = name_map.get(f.name, f.stem)

    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(new_map, f, ensure_ascii=False, indent=2)
        
    print(f"Toplam {renamed_count} PDF dosyası yeniden adlandırıldı.")

if __name__ == '__main__':
    main()
