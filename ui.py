import os
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont

from config import (
    FONT_CARD_TITLE,
    FONT_CARD_VAL,
    FONT_ENTRY,
    FONT_LABEL,
    FONT_MONO,
    FONT_TICKER,
    TEMALAR,
)
import market_service
import storage

# Pillow opsiyonel import - yoksa ikon oluşturma atlanır
try:
    from PIL import Image, ImageDraw
    _PILLOW_MEVCUT = True
except ImportError:
    _PILLOW_MEVCUT = False


def para_ikonu_uret(dosya_adi="fiya_para.ico"):
    """Windows'un sorunsuz tanıdığı .ico para simgesini oluşturur."""
    if not _PILLOW_MEVCUT:
        return None
    if not os.path.exists(dosya_adi):
        try:
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Yeşil banknot gövdesi
            draw.rectangle([2, 6, 29, 25], fill="#27ae60", outline="#1b4d2e", width=2)
            # Banknot köşeleri
            draw.point([(5, 9), (26, 9), (5, 22), (26, 22)], fill="#a9dfbf")
            # Altın sarısı rozet
            draw.ellipse([11, 10, 20, 21], fill="#f1c40f", outline="#b7950b")
            # Dolar simgesi çizgisi
            draw.line([16, 12, 16, 19], fill="#1b4d2e", width=1)
            draw.point([(15, 13), (17, 13), (15, 15), (17, 16), (15, 18), (17, 18)], fill="#1b4d2e")

            img.save(dosya_adi, format="ICO", sizes=[(16, 16), (32, 32)])
        except Exception:
            return None
    return dosya_adi


class HalkaArzApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fiya")
        self.root.geometry("1240x740")
        self.root.minsize(900, 600)

        # Pencere kapanma protokolü - temizlik için
        self.root.protocol("WM_DELETE_WINDOW", self._uygulama_kapat)

        # Windows Başlık Çubuğu Para İkonu
        try:
            ico_yolu = para_ikonu_uret()
            if ico_yolu:
                self.root.iconbitmap(default=ico_yolu)
        except Exception:
            pass

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.aktif_tema = "Aydınlık"
        self.dinamik_labellar = []
        self.drawer_acik = False
        self.ticker_text = "Piyasalar yükleniyor (BIST100, BIST30, NASDAQ, Dolar, Euro)..."
        self.ticker_offset = 0
        self._ticker_font = None
        self._ticker_text_width = 0
        self._after_ids = []  # after callback ID'lerini tut

        self._bilesenleri_olustur()
        self._olay_baglantilari()
        self.listeyi_guncelle()

        kayitli_veri = storage.verileri_oku()
        self.tema_uygula(kayitli_veri.get("tema", "Aydınlık"))

        self._ticker_kaydir()
        self._piyasa_guncelle_dongu()
        self._portfoy_guncelle_dongu()

    def _bilesenleri_olustur(self):
        # 1. ÜST ÇUBUK
        self.top_bar = tk.Frame(self.root, pady=4, padx=10)
        self.top_bar.pack(fill=tk.X)

        self.btn_drawer = tk.Button(
            self.top_bar,
            text="▼ Kayıtlı Hisselerim (Canlı)",
            font=FONT_ENTRY,
            relief=tk.RAISED,
            bd=2,
            padx=8,
            cursor="hand2",
        )
        self.btn_drawer.pack(side=tk.LEFT)

        self.btn_tema = tk.Button(self.top_bar, text="Tema Değiştir", font=FONT_ENTRY, relief=tk.RAISED, bd=2, padx=6)
        self.btn_tema.pack(side=tk.RIGHT)

        # 2. KAYAN BORSA BANDI
        self.ticker_frame = tk.Frame(self.root, height=26)
        self.ticker_frame.pack(fill=tk.X, padx=8, pady=(2, 4))
        self.ticker_frame.pack_propagate(False)

        self.ticker_canvas = tk.Canvas(self.ticker_frame, height=26, highlightthickness=0)
        self.ticker_canvas.pack(fill=tk.BOTH, expand=True)
        # Ticker fontunu başlat
        self._ticker_font = tkfont.Font(font=FONT_TICKER)

        # 3. SOL ÜST AÇILIR PANEL (DRAWER) - pack ile responsive
        self.drawer_frame = tk.Frame(self.root, relief=tk.GROOVE, bd=3)
        # Başlangıçta gizli, drawer_ac() içinde pack edilecek

        drawer_ust = tk.Frame(self.drawer_frame, pady=3, padx=5)
        drawer_ust.pack(fill=tk.X)

        self.lbl_drawer_title = tk.Label(drawer_ust, text="KAYITLI PORTFÖY ANLIK TAKİP", font=FONT_LABEL)
        self.lbl_drawer_title.pack(side=tk.LEFT)

        self.btn_drawer_kapat = tk.Button(drawer_ust, text="✖ Kapat", font=FONT_ENTRY, relief=tk.FLAT, bd=1, cursor="hand2")
        self.btn_drawer_kapat.pack(side=tk.RIGHT)

        kolonlar_drawer = ("kod", "fiyat", "degisim", "hacim")
        self.tree_drawer = ttk.Treeview(self.drawer_frame, columns=kolonlar_drawer, show="headings", height=7)
        self.tree_drawer.heading("kod", text="Hisse")
        self.tree_drawer.heading("fiyat", text="Son Fiyat")
        self.tree_drawer.heading("degisim", text="Günlük %")
        self.tree_drawer.heading("hacim", text="Hacim")

        self.tree_drawer.column("kod", width=70, anchor="center", stretch=True)
        self.tree_drawer.column("fiyat", width=90, anchor="e", stretch=True)
        self.tree_drawer.column("degisim", width=85, anchor="center", stretch=True)
        self.tree_drawer.column("hacim", width=95, anchor="e", stretch=True)
        self.tree_drawer.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        drawer_alt = tk.Frame(self.drawer_frame, pady=4, padx=6)
        drawer_alt.pack(fill=tk.X)

        self.btn_drawer_yukle = tk.Button(drawer_alt, text="Hesaplayıcıya Yükle", font=FONT_ENTRY, relief=tk.RAISED, bd=2)
        self.btn_drawer_yukle.pack(side=tk.LEFT, padx=2)

        self.btn_drawer_sil = tk.Button(drawer_alt, text="Listeden Sil", font=FONT_ENTRY, relief=tk.RAISED, bd=2)
        self.btn_drawer_sil.pack(side=tk.LEFT, padx=2)

        self.btn_drawer_yenile = tk.Button(drawer_alt, text="⟳ Şimdi Güncelle", font=FONT_ENTRY, relief=tk.RAISED, bd=2)
        self.btn_drawer_yenile.pack(side=tk.RIGHT, padx=2)

        # 4. ANA KONTEYNER
        self.main_container = tk.Frame(self.root, padx=8, pady=4)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ------------------ EN SOL: ANLIK DEĞİŞKEN VERİ KARTI ------------------
        self.kart_frame = tk.LabelFrame(self.main_container, text=" Canlı Piyasa Kartı ", font=FONT_LABEL, relief=tk.GROOVE, bd=2, width=220)
        self.kart_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self.kart_frame.pack_propagate(False)

        self.kart_ic = tk.Frame(self.kart_frame, padx=8, pady=8)
        self.kart_ic.pack(fill=tk.BOTH, expand=True)

        self.lbl_kart_hisse = tk.Label(self.kart_ic, text="SEMBOL: ---", font=FONT_CARD_TITLE, anchor="w")
        self.lbl_kart_hisse.pack(fill=tk.X, pady=(0, 10))

        metrikler = [
            ("Son Fiyat:", "lbl_kart_fiyat", "--- TL"),
            ("Günlük Değişim:", "lbl_kart_degisim", "--- %"),
            ("Gün İçi En Düşük:", "lbl_kart_dusuk", "--- TL"),
            ("Gün İçi En Yüksek:", "lbl_kart_yuksek", "--- TL"),
            ("Hacim (Adet):", "lbl_kart_hacim", "---"),
        ]

        self.kart_deger_widgetleri = {}
        for baslik, attr_name, varsayilan in metrikler:
            l_baslik = tk.Label(self.kart_ic, text=baslik, font=FONT_LABEL, anchor="w")
            l_baslik.pack(fill=tk.X, pady=(3, 0))
            self.dinamik_labellar.append(l_baslik)

            l_val = tk.Label(self.kart_ic, text=varsayilan, font=FONT_CARD_VAL, anchor="w", relief=tk.SUNKEN, bd=1, padx=4, pady=2)
            l_val.pack(fill=tk.X, pady=(0, 5))
            self.kart_deger_widgetleri[attr_name] = l_val

        # ------------------ ORTA: PARAMETRELER & HESAPLAMA ------------------
        self.sol_frame = tk.LabelFrame(self.main_container, text=" Parametreler & Günlük Simülasyon ", font=FONT_LABEL, relief=tk.GROOVE, bd=2)
        self.sol_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self.input_box = tk.Frame(self.sol_frame, pady=4)
        self.input_box.pack(fill=tk.X, padx=10)

        lbl_kod = tk.Label(self.input_box, text="Hisse Kodu / Adı:", font=FONT_LABEL)
        lbl_kod.grid(row=0, column=0, sticky="w", pady=2)

        self.kod_frame = tk.Frame(self.input_box)
        self.kod_frame.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        self.entry_kod = tk.Entry(self.kod_frame, font=FONT_ENTRY, relief=tk.SUNKEN, bd=2)
        self.entry_kod.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_veri_cek = tk.Button(self.kod_frame, text="Veri Çek", font=("MS Sans Serif", 8, "bold"), relief=tk.RAISED, bd=2, cursor="hand2")
        self.btn_veri_cek.pack(side=tk.RIGHT, padx=(4, 0))

        lbl_fiyat = tk.Label(self.input_box, text="Hisse Fiyatı (TL):", font=FONT_LABEL)
        lbl_fiyat.grid(row=1, column=0, sticky="w", pady=2)
        self.entry_fiyat = tk.Entry(self.input_box, font=FONT_ENTRY, relief=tk.SUNKEN, bd=2)
        self.entry_fiyat.grid(row=1, column=1, sticky="ew", pady=2, padx=5)

        lbl_gun = tk.Label(self.input_box, text="Gün Sayısı:", font=FONT_LABEL)
        lbl_gun.grid(row=2, column=0, sticky="w", pady=2)
        self.entry_gun = tk.Entry(self.input_box, font=FONT_ENTRY, relief=tk.SUNKEN, bd=2)
        self.entry_gun.grid(row=2, column=1, sticky="ew", pady=2, padx=5)

        lbl_adet = tk.Label(self.input_box, text="Adet:", font=FONT_LABEL)
        lbl_adet.grid(row=3, column=0, sticky="w", pady=2)
        self.entry_adet = tk.Entry(self.input_box, font=FONT_ENTRY, relief=tk.SUNKEN, bd=2)
        self.entry_adet.grid(row=3, column=1, sticky="ew", pady=2, padx=5)

        lbl_tip = tk.Label(self.input_box, text="İşlem Tipi:", font=FONT_LABEL)
        lbl_tip.grid(row=4, column=0, sticky="w", pady=2)
        self.combo_tip = ttk.Combobox(self.input_box, values=["Tavan", "Taban"], state="readonly", font=FONT_ENTRY)
        self.combo_tip.current(0)
        self.combo_tip.grid(row=4, column=1, sticky="ew", pady=2, padx=5)

        self.dinamik_labellar.extend([lbl_kod, lbl_fiyat, lbl_gun, lbl_adet, lbl_tip])
        self.input_box.columnconfigure(1, weight=1)

        self.btn_bar = tk.Frame(self.sol_frame)
        self.btn_bar.pack(fill=tk.X, padx=10, pady=8)

        self.btn_hesapla = tk.Button(self.btn_bar, text="[ HESAPLA ]", font=("MS Sans Serif", 10, "bold"), relief=tk.RAISED, bd=3, cursor="hand2")
        self.btn_hesapla.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_kaydet_direkt = tk.Button(self.btn_bar, text="[ KAYDET ]", font=("MS Sans Serif", 9, "bold"), relief=tk.RAISED, bd=2, cursor="hand2")
        self.btn_kaydet_direkt.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_temizle = tk.Button(self.btn_bar, text="[ TEMİZLE ]", font=("MS Sans Serif", 9, "bold"), relief=tk.RAISED, bd=2, cursor="hand2", width=10)
        self.btn_temizle.pack(side=tk.RIGHT)

        self.lbl_sonuc = tk.Label(self.sol_frame, text="Kümülatif Günlük Değişim:", font=FONT_LABEL)
        self.lbl_sonuc.pack(anchor="w", padx=10)

        self.text_sonuc = tk.Text(self.sol_frame, height=13, font=FONT_MONO, state=tk.DISABLED, relief=tk.SUNKEN, bd=2)
        self.text_sonuc.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 10))

        # ------------------ SAĞ: YÜZDESEL DEĞİŞİM TABLOLARI ------------------
        self.sag_frame = tk.Frame(self.main_container)
        self.sag_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.frame_arti = tk.LabelFrame(self.sag_frame, text=" Pozitif Olasılıklar (+%1 ~ +%10) ", font=FONT_LABEL, relief=tk.GROOVE, bd=2)
        self.frame_arti.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        kolonlar = ("oran", "fiyat", "toplam", "kz")
        self.tree_arti = ttk.Treeview(self.frame_arti, columns=kolonlar, show="headings", height=6)
        self.tree_arti.heading("oran", text="Oran")
        self.tree_arti.heading("fiyat", text="Birim Fiyat")
        self.tree_arti.heading("toplam", text="Portföy Değeri")
        self.tree_arti.heading("kz", text="Kâr")
        self.tree_arti.column("oran", width=55, anchor="center")
        self.tree_arti.column("fiyat", width=95, anchor="e")
        self.tree_arti.column("toplam", width=110, anchor="e")
        self.tree_arti.column("kz", width=95, anchor="e")
        self.tree_arti.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.frame_eksi = tk.LabelFrame(self.sag_frame, text=" Negatif Olasılıklar (-%1 ~ -%10) ", font=FONT_LABEL, relief=tk.GROOVE, bd=2)
        self.frame_eksi.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.tree_eksi = ttk.Treeview(self.frame_eksi, columns=kolonlar, show="headings", height=6)
        self.tree_eksi.heading("oran", text="Oran")
        self.tree_eksi.heading("fiyat", text="Birim Fiyat")
        self.tree_eksi.heading("toplam", text="Portföy Değeri")
        self.tree_eksi.heading("kz", text="Zarar")
        self.tree_eksi.column("oran", width=55, anchor="center")
        self.tree_eksi.column("fiyat", width=95, anchor="e")
        self.tree_eksi.column("toplam", width=110, anchor="e")
        self.tree_eksi.column("kz", width=95, anchor="e")
        self.tree_eksi.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 5. ALT DURUM ÇUBUĞU (v1.0.1)
        self.status_bar = tk.Frame(self.root, height=20, padx=6)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_versiyon = tk.Label(self.status_bar, text="v1.0.1", font=("MS Sans Serif", 8), anchor="e")
        self.lbl_versiyon.pack(side=tk.RIGHT)

    def _olay_baglantilari(self):
        self.btn_tema.config(command=self.tema_degistir)
        self.btn_veri_cek.config(command=self.canli_fiyat_cek)
        self.btn_hesapla.config(command=self.hesapla)
        self.btn_kaydet_direkt.config(command=self.hisse_kaydet)
        self.btn_temizle.config(command=self.ekrani_temizle)
        self.btn_drawer.config(command=self.drawer_toggle)
        self.btn_drawer_kapat.config(command=self.drawer_kapat)
        self.btn_drawer_yukle.config(command=self.hisse_yukle_drawer)
        self.btn_drawer_sil.config(command=self.hisse_sil_drawer)
        self.btn_drawer_yenile.config(command=self.portfoy_canli_guncelle)
        self.tree_drawer.bind("<Double-Button-1>", lambda e: self.hisse_yukle_drawer())

    def drawer_toggle(self):
        if self.drawer_acik:
            self.drawer_kapat()
        else:
            self.drawer_ac()

    def drawer_ac(self):
        # Drawer'ı main_container'ın üstüne pack et (sol üst köşe)
        self.drawer_frame.pack(in_=self.main_container, side=tk.TOP, anchor=tk.NW, fill=tk.X, padx=4, pady=4)
        self.drawer_frame.lift()
        self.drawer_acik = True
        self.btn_drawer.config(text="▲ Kayıtlı Hisselerim (Açık)")
        self.portfoy_canli_guncelle()

    def drawer_kapat(self):
        self.drawer_frame.pack_forget()
        self.drawer_acik = False
        self.btn_drawer.config(text="▼ Kayıtlı Hisselerim (Canlı)")

    def _ticker_kaydir(self):
        # Pencere kapatıldıysa durdur
        if not self.root.winfo_exists():
            return
            
        self.ticker_canvas.delete("all")
        renk = TEMALAR[self.aktif_tema]["ticker_fg"]
        
        # Metin genişliğini font ile ölç
        if self._ticker_font:
            self._ticker_text_width = self._ticker_font.measure(self.ticker_text)
        else:
            self._ticker_text_width = len(self.ticker_text) * 8  # fallback
        
        self.ticker_canvas.create_text(
            self.ticker_offset,
            13,
            text=self.ticker_text,
            anchor="w",
            fill=renk,
            font=FONT_TICKER,
        )

        canvas_width = self.ticker_canvas.winfo_width()
        if canvas_width <= 1:  # Henüz render edilmemiş
            canvas_width = 800

        self.ticker_offset -= 2
        if self.ticker_offset < -self._ticker_text_width:
            self.ticker_offset = canvas_width

        # after ID'sini kaydet temizlik için
        after_id = self.root.after(40, self._ticker_kaydir)
        self._after_ids.append(after_id)
        # Eski ID'leri temizle (bellek sızıntısı önleme)
        if len(self._after_ids) > 100:
            self._after_ids = self._after_ids[-50:]

    def _piyasa_guncelle_dongu(self):
        if not self.root.winfo_exists():
            return
            
        def bitti(metin):
            def guncelle():
                if self.root.winfo_exists():
                    self.ticker_text = metin
            self.root.after(0, guncelle)

        market_service.piyasa_ozet_getir(bitti)
        after_id = self.root.after(60000, self._piyasa_guncelle_dongu)
        self._after_ids.append(after_id)

    def portfoy_canli_guncelle(self):
        if not self.root.winfo_exists():
            return
            
        tam_veri = storage.verileri_oku()
        hisseler = list(tam_veri.get("hisseler", {}).keys())
        if not hisseler:
            for r in self.tree_drawer.get_children():
                self.tree_drawer.delete(r)
            return

        def bitti(sonuclar):
            def uygula():
                if not self.root.winfo_exists():
                    return
                for r in self.tree_drawer.get_children():
                    self.tree_drawer.delete(r)

                for kod in sorted(hisseler):
                    bilgi = sonuclar.get(kod)
                    if bilgi:
                        deg = bilgi["degisim"]
                        ok = "+" if deg > 0 else ""
                        self.tree_drawer.insert(
                            "",
                            tk.END,
                            values=(
                                kod,
                                f"{bilgi['fiyat']:.2f} TL",
                                f"{ok}{deg:.2f}%",
                                f"{bilgi['hacim']:,}",
                            ),
                        )
                    else:
                        self.tree_drawer.insert("", tk.END, values=(kod, "---", "---", "---"))

            self.root.after(0, uygula)

        market_service.toplu_hisse_fiyatlari_getir(hisseler, bitti)

    def _portfoy_guncelle_dongu(self):
        if not self.root.winfo_exists():
            return
        if self.drawer_acik:
            self.portfoy_canli_guncelle()
        after_id = self.root.after(30000, self._portfoy_guncelle_dongu)
        self._after_ids.append(after_id)

    def _uygulama_kapat(self):
        """Uygulama kapanırken tüm after callback'lerini iptal et ve temizlik yap."""
        for after_id in self._after_ids:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        self._after_ids.clear()
        self.root.destroy()

    def _tum_labelleri_topla(self):
        """Tüm Label widget'larını toplayan yardımcı fonksiyon."""
        labeller = []
        def topla(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Label):
                    labeller.append(child)
                elif isinstance(child, (tk.Frame, tk.LabelFrame, ttk.LabelFrame)):
                    topla(child)
        topla(self.root)
        return labeller

    def listeyi_guncelle(self):
        self.portfoy_canli_guncelle()

    def hisse_kaydet(self):
        kod = self.entry_kod.get().strip().upper()
        if not kod:
            messagebox.showwarning("Uyarı", "Lütfen bir hisse kodu/adı girin!")
            return

        fiyat = self.entry_fiyat.get().strip()
        gun = self.entry_gun.get().strip()
        adet = self.entry_adet.get().strip()
        tip = self.combo_tip.get()

        if not (fiyat and gun and adet):
            messagebox.showwarning("Uyarı", "Lütfen kaydetmeden önce tüm alanları doldurun!")
            return

        tam_veri = storage.verileri_oku()
        tam_veri["hisseler"][kod] = {"fiyat": fiyat, "gun": gun, "adet": adet, "tip": tip}
        storage.verileri_yaz(tam_veri)
        self.portfoy_canli_guncelle()
        messagebox.showinfo("Başarılı", f"'{kod}' başarıyla kaydedildi. Sol üstteki menüden anlık izleyebilirsiniz.")

    def hisse_sil_drawer(self):
        secili = self.tree_drawer.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Silmek için portföyden bir hisse seçin!")
            return

        kod = self.tree_drawer.item(secili[0])["values"][0]
        tam_veri = storage.verileri_oku()
        if kod in tam_veri.get("hisseler", {}):
            del tam_veri["hisseler"][kod]
            storage.verileri_yaz(tam_veri)
            self.portfoy_canli_guncelle()
            messagebox.showinfo("Silindi", f"'{kod}' silindi.")

    def hisse_yukle_drawer(self):
        secili = self.tree_drawer.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Yüklemek için bir hisse seçin!")
            return

        kod = str(self.tree_drawer.item(secili[0])["values"][0])
        tam_veri = storage.verileri_oku()
        hisseler = tam_veri.get("hisseler", {})
        if kod in hisseler:
            h = hisseler[kod]
            self.entry_kod.delete(0, tk.END)
            self.entry_kod.insert(0, kod)

            self.entry_fiyat.delete(0, tk.END)
            self.entry_fiyat.insert(0, h.get("fiyat", ""))

            self.entry_gun.delete(0, tk.END)
            self.entry_gun.insert(0, h.get("gun", ""))

            self.entry_adet.delete(0, tk.END)
            self.entry_adet.insert(0, h.get("adet", ""))

            self.combo_tip.set(h.get("tip", "Tavan"))
            self.canli_fiyat_cek()
            self.drawer_kapat()

    def canli_fiyat_cek(self):
        kod = self.entry_kod.get().strip().upper()
        if not kod:
            messagebox.showwarning("Uyarı", "Lütfen önce bir hisse kodu girin! (Örn: THYAO, EREGL)")
            return

        self.btn_veri_cek.config(state=tk.DISABLED, text="...")

        def basarili(sonuclar):
            def guncelle():
                self.entry_fiyat.delete(0, tk.END)
                self.entry_fiyat.insert(0, f"{sonuclar['son_fiyat']:.2f}")

                self.lbl_kart_hisse.config(text=f"SEMBOL: {sonuclar['kod']}")
                self.kart_deger_widgetleri["lbl_kart_fiyat"].config(text=f"{sonuclar['son_fiyat']:.2f} TL")

                degisim = sonuclar["degisim_yuzde"]
                isaret = "+" if degisim > 0 else ""
                renk_tag = "#008800" if degisim >= 0 else "#cc0000"
                if self.aktif_tema == "Karanlık":
                    renk_tag = "#00ff66" if degisim >= 0 else "#ff5555"

                self.kart_deger_widgetleri["lbl_kart_degisim"].config(text=f"{isaret}{degisim:.2f} %", fg=renk_tag)
                self.kart_deger_widgetleri["lbl_kart_dusuk"].config(text=f"{sonuclar['gun_dusuk']:.2f} TL")
                self.kart_deger_widgetleri["lbl_kart_yuksek"].config(text=f"{sonuclar['gun_yuksek']:.2f} TL")
                self.kart_deger_widgetleri["lbl_kart_hacim"].config(text=f"{sonuclar['hacim']:,}")

                self.btn_veri_cek.config(state=tk.NORMAL, text="Veri Çek")
            self.root.after(0, guncelle)

        def hata(mesaj):
            def goster():
                messagebox.showerror("Piyasa Hatası", mesaj)
                self.btn_veri_cek.config(state=tk.NORMAL, text="Veri Çek")
            self.root.after(0, goster)

        market_service.canli_veri_getir(kod, basarili, hata)

    # Tavan/Taban yüzdeleri (BIST standartları: %5, %8, %10, %20)
    TAVAN_ORANLARI = [0.05, 0.08, 0.10, 0.20]
    TABAN_ORANLARI = [-0.05, -0.08, -0.10, -0.20]

    def _guncel_oran_al(self, tip: str) -> float:
        """Hisse tipine göre güncel tavan/taban oranını döner.
        Gerçek uygulamada bu veriler bir API'den veya veritabanından alınmalıdır.
        Şimdilik varsayılan %10 kullanıyoruz."""
        # TODO: Gerçek tavan/taban verisi entegrasyonu
        return 0.10 if tip == "Tavan" else -0.10

    def hesapla(self):
        try:
            fiyat_str = self.entry_fiyat.get().replace(",", ".")
            gun = int(self.entry_gun.get())
            adet = int(self.entry_adet.get())
            tip = self.combo_tip.get()

            if gun <= 0 or adet <= 0:
                messagebox.showerror("Hata", "Gün sayısı ve adet 0'dan büyük olmalıdır!")
                return

            fiyat = float(fiyat_str)
            if fiyat <= 0:
                messagebox.showerror("Hata", "Fiyat 0'dan büyük olmalıdır!")
                return

            oran = self._guncel_oran_al(tip)
            maliyet = fiyat * adet

            hisse_kodu = self.entry_kod.get().strip().upper() or "HİSSE"

            sonuc_metni = f"[{hisse_kodu}] BAŞLANGIÇ: {fiyat:.2f} TL | Adet: {adet} | Maliyet: {maliyet:.2f} TL\n"
            sonuc_metni += f"İşlem Tipi: {tip} (Günlük Oran: %{abs(oran)*100:.0f})\n"
            sonuc_metni += "=" * 60 + "\n"

            guncel_fiyat = fiyat
            for i in range(1, gun + 1):
                guncel_fiyat *= 1 + oran
                toplam = guncel_fiyat * adet
                kar_zarar = toplam - maliyet
                sonuc_metni += f"{i:2d}. GÜN: {guncel_fiyat:8.2f} TL | Toplam: {toplam:10.2f} TL | K/Z: {kar_zarar:+10.2f} TL\n"

            self.text_sonuc.config(state=tk.NORMAL)
            self.text_sonuc.delete(1.0, tk.END)
            self.text_sonuc.insert(tk.END, sonuc_metni)
            self.text_sonuc.config(state=tk.DISABLED)

            # Pozitif olasılıklar tablosu (%1 - %10)
            for row in self.tree_arti.get_children():
                self.tree_arti.delete(row)
            for yuzde in range(1, 11):
                yeni_fiyat = fiyat * (1 + (yuzde / 100))
                yeni_toplam = yeni_fiyat * adet
                fark = yeni_toplam - maliyet
                self.tree_arti.insert("", tk.END, values=(f"+%{yuzde}", f"{yeni_fiyat:.2f} TL", f"{yeni_toplam:.2f} TL", f"+{fark:.2f} TL"))

            # Negatif olasılıklar tablosu (%1 - %10)
            for row in self.tree_eksi.get_children():
                self.tree_eksi.delete(row)
            for yuzde in range(1, 11):
                yeni_fiyat = fiyat * (1 - (yuzde / 100))
                yeni_toplam = yeni_fiyat * adet
                fark = yeni_toplam - maliyet
                self.tree_eksi.insert("", tk.END, values=(f"-%{yuzde}", f"{yeni_fiyat:.2f} TL", f"{yeni_toplam:.2f} TL", f"{fark:.2f} TL"))

        except ValueError:
            messagebox.showerror("Hata Oluştu", "Lütfen fiyat, gün ve adet alanlarına geçerli sayılar girin!")
        except Exception as e:
            messagebox.showerror("Hata Oluştu", f"Beklenmeyen bir hata oluştu:\n{e}")

    def ekrani_temizle(self):
        for ent in [self.entry_kod, self.entry_fiyat, self.entry_gun, self.entry_adet]:
            ent.delete(0, tk.END)
        self.combo_tip.current(0)

        self.text_sonuc.config(state=tk.NORMAL)
        self.text_sonuc.delete(1.0, tk.END)
        self.text_sonuc.config(state=tk.DISABLED)

        for row in self.tree_arti.get_children():
            self.tree_arti.delete(row)
        for row in self.tree_eksi.get_children():
            self.tree_eksi.delete(row)

        self.lbl_kart_hisse.config(text="SEMBOL: ---")
        for val_lbl in self.kart_deger_widgetleri.values():
            val_lbl.config(text="---", fg=TEMALAR[self.aktif_tema]["fg"])

        self.entry_kod.focus()

    def tema_uygula(self, tema_adi):
        self.aktif_tema = tema_adi
        renk = TEMALAR[tema_adi]

        self.root.configure(bg=renk["bg"])
        self.top_bar.configure(bg=renk["bg"])
        self.main_container.configure(bg=renk["bg"])

        # Status Bar
        self.status_bar.configure(bg=renk["bg"])
        self.lbl_versiyon.configure(bg=renk["bg"], fg=renk["fg"])

        # Ticker Frame
        self.ticker_frame.configure(bg=renk["ticker_bg"])
        self.ticker_canvas.configure(bg=renk["ticker_bg"])

        # Drawer Frame
        self.drawer_frame.configure(bg=renk["drawer_bg"])
        self.lbl_drawer_title.configure(bg=renk["drawer_bg"], fg=renk["fg"])
        self.btn_drawer.configure(bg=renk["btn_bg"], fg=renk["btn_fg"])
        self.btn_drawer_kapat.configure(bg=renk["btn_bg"], fg=renk["btn_fg"])
        self.btn_drawer_yukle.configure(bg=renk["btn_bg"], fg=renk["btn_fg"])
        self.btn_drawer_sil.configure(bg=renk["btn_bg"], fg=renk["btn_fg"])
        self.btn_drawer_yenile.configure(bg=renk["btn_bg"], fg=renk["btn_fg"])

        # Kart & Girdi Çerçeveleri
        self.kart_frame.configure(bg=renk["bg"], fg=renk["fg"])
        self.kart_ic.configure(bg=renk["bg"])
        self.lbl_kart_hisse.configure(bg=renk["bg"], fg=renk["card_fg"])

        for val_lbl in self.kart_deger_widgetleri.values():
            val_lbl.configure(bg=renk["entry_bg"], fg=renk["entry_fg"])

        self.sol_frame.configure(bg=renk["bg"], fg=renk["fg"])
        self.input_box.configure(bg=renk["bg"])
        self.kod_frame.configure(bg=renk["bg"])
        self.btn_bar.configure(bg=renk["bg"])
        self.lbl_sonuc.configure(bg=renk["bg"], fg=renk["fg"])

        self.sag_frame.configure(bg=renk["bg"])
        self.frame_arti.configure(bg=renk["bg"], fg=renk["fg"])
        self.frame_eksi.configure(bg=renk["bg"], fg=renk["fg"])

        # Tüm label'ları dinamik topla ve renklendir
        for lbl in self._tum_labelleri_topla():
            try:
                lbl.configure(bg=renk["bg"], fg=renk["fg"])
            except Exception:
                pass

        for ent in [self.entry_kod, self.entry_fiyat, self.entry_gun, self.entry_adet]:
            ent.configure(bg=renk["entry_bg"], fg=renk["entry_fg"], insertbackground=renk["entry_fg"])

        self.text_sonuc.configure(bg=renk["entry_bg"], fg=renk["entry_fg"], insertbackground=renk["entry_fg"])

        self.btn_hesapla.configure(bg=renk["calc_btn_bg"], fg=renk["calc_btn_fg"], activebackground=renk["bg"])
        self.btn_kaydet_direkt.configure(bg=renk["btn_bg"], fg=renk["btn_fg"], activebackground=renk["bg"])
        self.btn_temizle.configure(bg=renk["btn_bg"], fg=renk["btn_fg"], activebackground=renk["bg"])
        self.btn_veri_cek.configure(bg=renk["btn_bg"], fg=renk["btn_fg"], activebackground=renk["bg"])

        self.btn_tema.configure(
            text=f"Tema: {tema_adi} [{'🌙' if tema_adi == 'Karanlık' else '☀️'}]",
            bg=renk["btn_bg"],
            fg=renk["btn_fg"],
        )

        self.style.configure(
            "Treeview",
            background=renk["tree_bg"],
            fieldbackground=renk["tree_bg"],
            foreground=renk["tree_fg"],
            rowheight=19,
        )
        self.style.configure(
            "Treeview.Heading",
            background=renk["tree_head_bg"],
            foreground=renk["tree_head_fg"],
            relief="raised",
        )
        self.style.map("Treeview", background=[("selected", renk["tree_selected"])])

        tam_veri = storage.verileri_oku()
        tam_veri["tema"] = tema_adi
        storage.verileri_yaz(tam_veri)

    def tema_degistir(self):
        yeni_tema = "Karanlık" if self.aktif_tema == "Aydınlık" else "Aydınlık"
        self.tema_uygula(yeni_tema)