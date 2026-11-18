# 💧 Water Reminder

[![CI](https://github.com/hamzakabakcili-ui/water-reminder/actions/workflows/ci.yml/badge.svg)](https://github.com/hamzakabakcili-ui/water-reminder/actions/workflows/ci.yml)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A lightweight macOS reminder that nudges you to drink water and refill your thermos during the workday. No dependencies, no accounts, everything runs locally.

**Hafta içi mesai boyunca su içmeyi ve termosu doldurmayı hatırlatan, tamamen yerel çalışan küçük bir macOS uygulaması.**

<p align="center">
  <img src="docs/screenshot.png" alt="Water Reminder popup" width="480">
</p>

## Quick start (English)

```bash
git clone https://github.com/hamzakabakcili-ui/water-reminder.git
cd water-reminder
python3 su_hatirlatici.py --install-autostart   # asks 4 questions, then runs at every login
```

On first use (either `--install-autostart` or a plain `python3 su_hatirlatici.py`) four notification-style cards appear in the bottom-right corner of your screen: daily goal, work start, work end and thermos size. Pick with the mouse; the white button is the suggested value. Reminders then start on the **next workday**.

- Change settings later: `python3 su_hatirlatici.py --ayarla` (or with flags, see below).
- Preview one reminder: `python3 su_hatirlatici.py --test`.
- Keep the cloned folder where it is: the login item points at it.
- After `git pull`, restart the background process (see "Güncelleme").

Requires macOS and Python 3.9+. The UI is in Turkish only.

## Özellikler

- Hafta içi (Pazartesi–Cuma), seçtiğiniz saatler arasında çalışır (varsayılan 09:30–18:00), hafta sonu susar.
- Ekranın **sağ altında** renkli, dikkat çekici bir kart açar: su içme mavi, termos doldurma turuncu, kurulum mor, gün sonu özeti yeşil. Günlük hedefe ilerleme çubuğu gösterir.
- Kart klavye odağını asla almaz: yazarken tuşların hepsi kendi uygulamana gider, bip sesi çıkmaz. Sadece fareyle kullanılır.
- Termosun içindeki miktarı takip eder ve bittiğinde "doldur" der.
- Hedefe (varsayılan 2,5 L) ilerlemeyi gösterir, gün sonunda özet verir.
- Hiçbir şey kurmanız gerekmez: sadece Python 3 ve macOS'un kendi araçlarını kullanır.

## Gereksinimler

- macOS (pencere için `osascript` / AppKit kullanır)
- Python 3.9 veya üzeri (macOS ile gelen `/usr/bin/python3` yeterli)
- Mac'inizde Komut Satırı Araçları (Command Line Tools) kurulu değilse, ilk `git` ya da `python3` çağrısında macOS bir kurulum penceresi açar. Kurulum bitince komutu tekrar çalıştırın.

## Kurulum ve ilk kullanım

```bash
git clone https://github.com/hamzakabakcili-ui/water-reminder.git
cd water-reminder
python3 su_hatirlatici.py --install-autostart
```

1. Ekranın sağ altında sırayla dört kart çıkar: **günlük hedef**, **mesai başlangıcı**, **mesai bitişi**, **termos/bardak hacmi**. Fareyle seçin; beyaz buton önerilen değerdir. Terminal gerekmez, [Claude Code](https://claude.com/claude-code) ile kurulumda da çıkar.
2. Yeşil bir özet kartı seçimlerinizi gösterir.
3. Arka plan süreci kurulur (launchd). Her oturum açılışında kendiliğinden başlar.
4. Hatırlatmalar **bugün değil, bir sonraki iş gününden** başlar. Cuma akşamı kurarsanız ilk hatırlatma Pazartesi gelir.

Sorular sadece ayar dosyası yokken sorulur. Düz `python3 su_hatirlatici.py` ile (kurmadan, terminalde çalıştırarak) başlasanız da aynı sorular çıkar. Cevaplamazsanız (5 dakika) varsayılanlar kaydedilir ve hatırlatmalar hemen başlar.

> Klonladığınız klasörü silmeyin ya da taşımayın: otomatik başlatma dosyanın yolunu saklar. Taşırsanız `--install-autostart` komutunu yeni konumdan tekrar çalıştırın.

## Günlük kullanım

```bash
python3 su_hatirlatici.py                      # çalıştır (kurmadan, terminalde)
python3 su_hatirlatici.py --test               # hemen bir hatırlatma göster
python3 su_hatirlatici.py --skip-today         # sadece bugün için sustur
python3 su_hatirlatici.py --uninstall-autostart
```

Mesai boyunca yaklaşık 30 dakikada bir (süre hedefe göre otomatik hesaplanır) bir kart gelir:

- **Su içme kartı** (mavi): "Birkaç yudum su iç". Butonlar **İçtim** ve **Ertele**. Termosta kalan miktar ve günlük ilerleme kartta yazar.
- **Doldurma kartı** (turuncu): "Termos bitti!". Butonlar **Doldurdum, içtim** ve **Ertele**.
- **Ertele** 5 dakika sonra tekrar sorar. 90 saniye cevap verilmezse kart kapanır ve ertelenmiş sayılır.
- Termos 3 hatırlatmada biter (150 + 150 + 200 ml). Dördüncüsü yine "doldur" der, yani 5 termos = 2,5 L. Gün başında termos boş varsayılır, ilk kart "doldur"dur.
- Mesai bitince bir **gün sonu özeti** gelir. Ertesi gün sayaç sıfırlanır.
- Bilgisayar uykudan uyandığında, mesai saatindeyse ve hatırlatma vakti geçmişse tek bir hatırlatma hemen gelir. Kaçırılan hatırlatmalar birikmez.

## Ayarlar

Dört şeyi kendinize göre seçebilirsiniz: **günlük hedef** (0,5–6 L), **mesai başlangıcı** ve **bitişi**, **termos/bardak büyüklüğü** (100–2000 ml).

```bash
python3 su_hatirlatici.py --ayarla    # sorularla seç (boş bırakırsan mevcut değer kalır)

# ya da tek satırda (kurulum kartlarında olmayan değerler için de bunu kullanın):
python3 su_hatirlatici.py --ayarla --hedef-litre 3 --baslangic 08:30 --bitis 17:00 --kap-ml 330
```

Seçimler `~/.su_hatirlatici_ayar.json` dosyasına kaydedilir. Çalışan hatırlatıcı yeniden başlatmadan birkaç saniye içinde yeni ayarı alır. Hatalı girişler (ters saat, çok küçük/büyük hedef) Türkçe hata verir ve kaydedilmez.

Hatırlatma aralığı sizin için otomatik hesaplanır: hedefe mesai bitmeden ulaşacak şekilde (varsayılanda 30 dk, en az 10, en çok 60 dk). Bardak 150 ml'den küçükse yudum bardak kadar olur. Gün içinde kap küçültülürse termostaki miktar kırpılır.

Hafta içi / hafta sonu günleri sabittir (Pazartesi–Cuma). Diğer sabitler (`SIP_ML`, `SNOOZE_MIN`) [`su_hatirlatici.py`](su_hatirlatici.py) dosyasının en üstündedir. Günlük ilerleme `~/.su_hatirlatici.json` dosyasında tutulur ve her gün sıfırlanır. Bugünü sıfırlamak için bu dosyayı silin.

## Güncelleme

```bash
cd water-reminder
git pull
launchctl kickstart -k gui/$(id -u)/local.su-hatirlatici   # arka plan sürecini yeni kodla yeniden başlat
```

Arka plandaki süreç kodu başlarken yükler. Yeniden başlatmazsanız `git pull`'dan sonra da eski sürüm çalışmaya devam eder.

## Nasıl çalışır?

- [`su_hatirlatici.py`](su_hatirlatici.py): zamanlama, termos/günlük sayaç durumu, ayarlar, ilk kurulum soruları ve otomatik başlatma (launchd).
- [`popup.js`](popup.js): AppKit ile çizilen, ekranın sağ altına sabitlenen kart (`osascript -l JavaScript`). Basılan butonu stdout'a yazar.

Neden Tkinter değil? macOS'un yerleşik Tk'si yeni macOS sürümlerinde çöküyor, `display dialog` ise konumlandırılamıyor.

## Testler

```bash
python3 -m unittest discover -s tests -v
```

Testler zamanlamayı, ayarları, ilk kurulum akışını, durum kaydını ve hatırlatma mantığını kapsar. Pencere açmazlar, gerçek durum dosyana dokunmazlar. Her gönderimde GitHub Actions ile çalışırlar.

## Lisans

[MIT](LICENSE)
