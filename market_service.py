import threading
import time
import yfinance as yf
from functools import lru_cache

PIYASA_SEMBALLERI = {
    "BIST 100": "XU100.IS",
    "BIST 30": "XU030.IS",
    "NASDAQ": "^IXIC",
    "USD/TRY": "USDTRY=X",
    "EUR/TRY": "EURTRY=X",
}

# Basit in-memory cache: {symbol: (timestamp, data)}
_VERI_CACHE = {}
_CACHE_TTL = 10  # saniye

def _sembol_duzenle(kod: str) -> str:
    """Hisse kodunu yfinance formatına çevirir."""
    kod = kod.strip().upper()
    if kod.endswith(".IS") or kod.startswith("^") or "=" in kod:
        return kod
    return f"{kod}.IS"

def _cache_al(sembol: str):
    """Cache'den veri alır, yoksa/eskise None döner."""
    if sembol in _VERI_CACHE:
        ts, data = _VERI_CACHE[sembol]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None

def _cache_yaz(sembol: str, data: dict):
    _VERI_CACHE[sembol] = (time.time(), data)

def _hata_ayikla(e: Exception, kod: str) -> str:
    """yfinance hatalarını kullanıcı dostu mesaja çevirir."""
    msg = str(e).lower()
    if "rate limit" in msg or "too many requests" in msg:
        return f"'{kod}': API limitine ulaşıldı. Lütfen biraz bekleyin."
    if "no data" in msg or "not found" in msg or "404" in msg:
        return f"'{kod}': Sembol bulunamadı veya veri yok."
    if "timeout" in msg or "connection" in msg or "network" in msg:
        return f"'{kod}': Ağ bağlantısı hatası. İnternet kontrol edin."
    return f"'{kod}': Veri alınırken hata: {e}"

def canli_veri_getir(kod: str, basarili_cb, hata_cb):
    def gorev():
        try:
            sembol = _sembol_duzenle(kod)
            
            # Cache kontrolü
            cached = _cache_al(sembol)
            if cached:
                basarili_cb(cached)
                return

            ticker = yf.Ticker(sembol)
            gecmis = ticker.history(period="2d")

            if gecmis.empty:
                hata_cb(f"'{kod}' için veri bulunamadı.")
                return

            son_fiyat = float(gecmis["Close"].iloc[-1])
            onceki = float(gecmis["Close"].iloc[-2]) if len(gecmis) > 1 else son_fiyat
            degisim = ((son_fiyat - onceki) / onceki) * 100

            sonuclar = {
                "kod": kod,
                "son_fiyat": son_fiyat,
                "degisim_yuzde": degisim,
                "gun_dusuk": float(gecmis["Low"].iloc[-1]),
                "gun_yuksek": float(gecmis["High"].iloc[-1]),
                "hacim": int(gecmis["Volume"].iloc[-1]),
            }
            _cache_yaz(sembol, sonuclar)
            basarili_cb(sonuclar)
        except Exception as e:
            hata_cb(_hata_ayikla(e, kod))

    threading.Thread(target=gorev, daemon=True).start()

def piyasa_ozet_getir(tamamlandi_cb):
    def gorev():
        metin_parcalari = []
        for etiket, sembol in PIYASA_SEMBALLERI.items():
            try:
                cached = _cache_al(sembol)
                if cached:
                    son = cached["son_fiyat"]
                    deg = cached["degisim_yuzde"]
                else:
                    ticker = yf.Ticker(sembol)
                    gecmis = ticker.history(period="2d")
                    if gecmis.empty:
                        continue
                    son = float(gecmis["Close"].iloc[-1])
                    onceki = float(gecmis["Close"].iloc[-2]) if len(gecmis) > 1 else son
                    deg = ((son - onceki) / onceki) * 100
                    _cache_yaz(sembol, {"son_fiyat": son, "degisim_yuzde": deg})
                
                ok = "▲" if deg >= 0 else "▼"
                metin_parcalari.append(f"{etiket}: {son:,.2f} ({ok} %{abs(deg):.2f})")
            except Exception:
                continue

        if metin_parcalari:
            sonuc = "   |   ".join(metin_parcalari)
        else:
            sonuc = "Piyasa verisi bekleniyor..."
        tamamlandi_cb(sonuc)

    threading.Thread(target=gorev, daemon=True).start()

def toplu_hisse_fiyatlari_getir(kod_listesi: list, tamamlandi_cb):
    if not kod_listesi:
        tamamlandi_cb({})
        return

    def gorev():
        sonuclar = {}
        for kod in kod_listesi:
            try:
                sembol = _sembol_duzenle(kod)
                
                cached = _cache_al(sembol)
                if cached:
                    sonuclar[kod] = {
                        "fiyat": cached["son_fiyat"],
                        "degisim": cached["degisim_yuzde"],
                        "dusuk": cached["gun_dusuk"],
                        "yuksek": cached["gun_yuksek"],
                        "hacim": cached["hacim"],
                    }
                    continue

                ticker = yf.Ticker(sembol)
                gecmis = ticker.history(period="2d")
                if not gecmis.empty:
                    son = float(gecmis["Close"].iloc[-1])
                    onceki = float(gecmis["Close"].iloc[-2]) if len(gecmis) > 1 else son
                    deg = ((son - onceki) / onceki) * 100
                    data = {
                        "fiyat": son,
                        "degisim": deg,
                        "dusuk": float(gecmis["Low"].iloc[-1]),
                        "yuksek": float(gecmis["High"].iloc[-1]),
                        "hacim": int(gecmis["Volume"].iloc[-1]),
                    }
                    _cache_yaz(sembol, {
                        "son_fiyat": son,
                        "degisim_yuzde": deg,
                        "gun_dusuk": data["dusuk"],
                        "gun_yuksek": data["yuksek"],
                        "hacim": data["hacim"],
                    })
                    sonuclar[kod] = data
            except Exception:
                continue
        tamamlandi_cb(sonuclar)

    threading.Thread(target=gorev, daemon=True).start()