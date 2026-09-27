# Fiya - Halka Arz & Portföy Takip Uygulaması

Borsa İstanbul (BIST) hisse senetleri için canlı fiyat takibi, tavan/taban simülasyonu ve portföy yönetimi yapan masaüstü uygulaması.

## Özellikler

- **Canlı Piyasa Verileri**: yfinance üzerinden BIST hisse fiyatları, endeksler (BIST 100, BIST 30), NASDAQ, Dolar/TL, Euro/TL
- **Portföy Takibi**: Kayıtlı hisselerin anlık fiyat, günlük değişim, hacim bilgileri
- **Tavan/Taban Simülasyonu**: Günlük getiri hesaplaması ve kâr/zarar tabloları
- **Yüzdelik Olasılık Tabloları**: +%1'den +%10'a ve -%1'den -%10'a kadar senaryolar
- **Karanlık/Aydınlık Tema**: Tam renk teması desteği
- **Kaydırıcı Ticker Bandı**: Piyasa özetini sürekli güncellenen band ile takip
- **Veri Kalıcılığı**: JSON dosyasında hisse kayıtları ve tema tercihi

## Kurulum

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı çalıştır
python main.py
```

## Kullanım

1. **Hisse Kodu Girin**: Örn: `THYAO`, `EREGL`, `GARAN` (`.IS` eki otomatik eklenir)
2. **Veri Çek**: "Veri Çek" butonuyla canlı fiyatı getirin
3. **Parametreleri Ayarlayın**: Fiyat, gün sayısı, adet, işlem tipi (Tavan/Taban)
4. **Hesapla**: Kümülatif getiri ve olasılık tablolarını görüntüleyin
5. **Kaydet**: Portföyünüze ekleyin, sol üst menüden anlık izleyin

## Klavye Kısayolları

- `Enter`: Hesapla butonunu tetikler (odaklanma durumunda)
- `Escape`: Ekranı temizler

## Proje Yapısı

```
Halkarz/
├── main.py              # Giriş noktası
├── ui.py                # Tkinter arayüzü (ana mantık)
├── config.py            # Tema, font, sabitler
├── market_service.py    # yfinance veri çekme, cache
├── storage.py           # JSON okuma/yazma (atomik)
├── hisseler.json        # Kayıtlı veriler (otomatik oluşur)
├── requirements.txt     # Bağımlılıklar
└── fiya_para.ico        # Uygulama ikonu (otomatik oluşur)
```

## Teknik Detaylar

- **Thread-safe**: Ağ istekleri arka plan thread'inde, UI güncellemeleri `root.after()` ile ana thread'de
- **Cache**: 10 saniyelik basit in-memory cache ile rate limit koruması
- **Atomik Yazma**: `tempfile.NamedTemporaryFile + os.replace` ile veri bozulması önlenir
- **Cross-platform Font**: Windows/macOS/Linux'ta uygun sistem fontları
- **Memory Leak Koruması**: `after` callback ID'leri takip edilip kapanışta temizlenir

## Veri Güncelleme Sıklığı

| Bileşen | Sıklık | Açıklama |
|---------|--------|----------|
| **Piyasa Ticker Bandı** (BIST 100, BIST 30, NASDAQ, USD/TRY, EUR/TRY) | **60 saniye** | Üst kısımda kayan band, genel piyasa özeti |
| **Portföy / Drawer** (kayıtlı hisseler) | **30 saniye** | Sol üst "Kayıtlı Hisselerim" panelindeki anlık fiyatlar |
| **Manuel "Şimdi Güncelle"** | Anlık | Drawer'daki ⟳ butonuyla kullanıcı tetikler |
| **Veri Çek (Hesaplayıcı)** | Anlık | "Veri Çek" butonuyla tek seferlik sorgu |

> ⚠️ **Not**: yfinance API rate limitlerine tabidir. 10 saniyelik önbellek (cache) mekanizması ile aynı sembol için ardışık istekler yerel önbellekten karşılanır.

## Bilinen Sınırlamalar

- Tavan/taban oranları sabit %10 olarak varsayılmıştır (gerçek veriler BIST'ten alınmalıdır)
- yfinance rate limitleri geçici hatalara yol açabilir (cache ile azaltılmıştır)
- Pillow kütüphanesi yoksa uygulama ikonu oluşturulmaz (opsiyonel)

## Lisans

MIT License