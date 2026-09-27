import json
import os
import tempfile
from config import VERI_DOSYASI

def _dosya_dizini_hazirla():
    """Veri dosyasının dizinini oluşturur."""
    dizin = os.path.dirname(VERI_DOSYASI)
    if dizin and not os.path.exists(dizin):
        os.makedirs(dizin, exist_ok=True)

def verileri_oku() -> dict:
    """Verileri okur, eski formatı yeni formata çevirir."""
    varsayilan = {"hisseler": {}, "tema": "Aydınlık"}
    
    if not os.path.exists(VERI_DOSYASI):
        return varsayilan
    
    try:
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (json.JSONDecodeError, OSError):
        return varsayilan
    
    # Eski format kontrolü: {"KOD": {...}} -> {"hisseler": {...}, "tema": ...}
    if "hisseler" not in veri:
        hisseler = veri
        tema = "Aydınlık"
    else:
        hisseler = veri.get("hisseler", {})
        tema = veri.get("tema", "Aydınlık")
    
    # Geçersiz verileri temizle
    temiz_hisseler = {}
    for kod, bilgi in hisseler.items():
        if isinstance(bilgi, dict) and all(k in bilgi for k in ("fiyat", "gun", "adet", "tip")):
            temiz_hisseler[kod.upper()] = {
                "fiyat": str(bilgi["fiyat"]),
                "gun": str(bilgi["gun"]),
                "adet": str(bilgi["adet"]),
                "tip": str(bilgi["tip"]),
            }
    
    return {"hisseler": temiz_hisseler, "tema": tema}

def verileri_yaz(veri: dict) -> bool:
    """Verileri atomik olarak yazar (geçici dosya + replace)."""
    _dosya_dizini_hazirla()
    
    try:
        # Atomik yazma: geçici dosyaya yaz, sonra rename et
        with tempfile.NamedTemporaryFile(
            mode="w", 
            encoding="utf-8", 
            dir=os.path.dirname(VERI_DOSYASI) or ".",
            delete=False,
            suffix=".tmp"
        ) as tmp:
            json.dump(veri, tmp, ensure_ascii=False, indent=4)
            tmp_path = tmp.name
        
        # Windows'ta replace için önce hedefi silmek gerekebilir
        if os.path.exists(VERI_DOSYASI):
            os.replace(tmp_path, VERI_DOSYASI)
        else:
            os.rename(tmp_path, VERI_DOSYASI)
        return True
    except OSError:
        # Geçici dosyayı temizle
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass
        return False