# Posiadane filamenty

Prosta aplikacja webowa do śledzenia filamentów do druku 3D. Działa w przeglądarce,
przeznaczona na domowy serwer / Raspberry Pi. Dane trzymane są na serwerze (SQLite),
więc widać je z każdego urządzenia w sieci domowej (komputer, telefon, tablet).

## Funkcje

Każdy filament to **bloczek** z **grubą ramką w kolorze filamentu** — dzięki temu
łatwo go znaleźć wzrokiem, nawet przy 40 szpulach. Bloczek pokazuje wszystkie dane:

- **Rodzaj** – PLA / PETG / Inne.
- **Kolor** – nazwa (np. „czerwony") oraz wybrany kolor ramki (próbnik kolorów;
  wpisanie znanej polskiej nazwy automatycznie podpowiada kolor).
- **Gramatura teraz / po zakupie** + pasek postępu pokazujący, ile zostało.
- **Data zakupu** (`dd/mm/rrrr`).

**Kliknięcie bloczka** otwiera okno, w którym:

- w sekcji **Zużycie** wpisujesz, ile gramów zużyto, i klikasz **Zużyj** – ilość
  odejmuje się od stanu; **Cofnij** przywraca ostatnie odjęcie (można cofać kolejno);
- w sekcji **Szczegóły** edytujesz rodzaj, kolor, kolor ramki, gramaturę i datę
  (zmiany zapisują się od razu);
- przyciskiem **Usuń** kasujesz szpulę.

Bloczek **podświetla się na czerwono** (znacznik „niski stan"), gdy stan spadnie do
**300 g lub mniej** (próg ustawisz w `app.py` → `LOW_STOCK_THRESHOLD`).

Nad siatką jest licznik szpul, **filtry: rodzaj** (Wszystkie / PLA / PETG / Inne —
z liczbą szpul w każdej kategorii) i **kolor** (lista kolorów obecnych w magazynie,
z liczbą szpul i próbką barwy) — oba działają razem — oraz **sortowanie wg daty
zakupu** (rosnąco / malejąco).
Na telefonie bloczki układają się w 2 kolumny; na komputerze jest ich więcej w rzędzie.

## Wymagania

- Python 3.9+ (Raspberry Pi OS ma go w zestawie).

## Instalacja

```bash
cd ~/tunia                       # katalog z aplikacją
python3 -m venv .venv            # środowisko wirtualne
.venv/bin/pip install -r requirements.txt
```

> Na świeżym Raspberry Pi OS, gdyby `venv` zgłaszał błąd:
> `sudo apt install -y python3-venv`

## Uruchomienie

**Szybki start (serwer deweloperski):**

```bash
.venv/bin/python app.py
```

**Zalecane na stałe (serwer produkcyjny waitress):**

```bash
.venv/bin/waitress-serve --host=0.0.0.0 --port=5000 app:app
```

Następnie w przeglądarce (na dowolnym urządzeniu w sieci):

```
http://<adres-ip-raspberry>:5000
```

Adres IP Raspberry sprawdzisz poleceniem `hostname -I`. Na samym Pi działa też
`http://localhost:5000`.

## Autostart przy włączeniu Raspberry Pi (systemd)

1. Dostosuj ścieżki/użytkownika w `deploy/filamenty.service`
   (domyślnie użytkownik `pi` i katalog `/home/pi/tunia`).
2. Zainstaluj usługę:

```bash
sudo cp deploy/filamenty.service /etc/systemd/system/filamenty.service
sudo systemctl daemon-reload
sudo systemctl enable --now filamenty.service
```

3. Status / logi:

```bash
systemctl status filamenty.service
journalctl -u filamenty.service -f
```

## Dane i kopia zapasowa

Wszystkie dane są w jednym pliku `filaments.db` (SQLite) w katalogu aplikacji.
Kopia zapasowa = skopiowanie tego pliku. Usunięcie pliku = czysty start.

## Struktura

```
app.py                    # backend Flask + API + baza SQLite
templates/index.html      # interfejs (bloczki, edycja, filtr, sortowanie)
requirements.txt          # zależności
deploy/filamenty.service  # usługa systemd (autostart)
filaments.db              # baza danych (tworzona automatycznie)
```
