# Instalacja na Raspberry Pi — krok po kroku

Przewodnik instalacji aplikacji **Posiadane filamenty** na Raspberry Pi tak, aby
działała w tle i była dostępna w przeglądarce z każdego urządzenia w sieci domowej.

Założenia: Raspberry Pi z **Raspberry Pi OS** (dawniej Raspbian) i dostępem do
internetu. Komendy wykonujesz na Pi — bezpośrednio (klawiatura + monitor) albo
zdalnie przez SSH.

---

## Krok 1 — Skopiuj aplikację na Raspberry Pi

Wybierz **jedną** z metod. Docelowo pliki mają trafić do katalogu `~/tunia`
(czyli np. `/home/pi/tunia`).

### A) Z pendrive'a / innego komputera (scp)

Na komputerze, gdzie są pliki, wykonaj (podmień `pi` i adres IP Pi):

```bash
scp -r /home/nkg/tunia pi@ADRES-IP-RASPBERRY:~/tunia
```

> `.venv` i `filaments.db` nie są potrzebne do przeniesienia — środowisko
> stworzysz na Pi od nowa (Krok 3).

### B) Z GitHuba (jeśli wcześniej wypchniesz repozytorium)

```bash
cd ~
git clone ADRES-TWOJEGO-REPO tunia
```

### C) Bezpośrednio na Pi

Jeśli pliki już są na Pi — po prostu przejdź do katalogu:

```bash
cd ~/tunia
```

---

## Krok 2 — Zainstaluj Pythona i moduł venv

Raspberry Pi OS ma Pythona 3 w zestawie, ale upewnij się, że jest moduł `venv`:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
```

---

## Krok 3 — Utwórz środowisko i zainstaluj zależności

```bash
cd ~/tunia
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

To zainstaluje **Flask** i **waitress** (lekki serwer produkcyjny) w izolowanym
środowisku, bez ruszania systemowego Pythona.

---

## Krok 4 — Pierwsze uruchomienie (test)

```bash
.venv/bin/waitress-serve --host=0.0.0.0 --port=5000 app:app
```

Na samym Pi otwórz w przeglądarce `http://localhost:5000`.
Plik bazy `filaments.db` utworzy się automatycznie. Zatrzymanie testu: `Ctrl + C`.

---

## Krok 5 — Dostęp z innych urządzeń (telefon, laptop)

Sprawdź adres IP Raspberry:

```bash
hostname -I
```

Pierwszy adres (np. `192.168.1.50`) wpisz na innym urządzeniu w przeglądarce:

```
http://192.168.1.50:5000
```

> Wszystkie urządzenia muszą być w tej samej sieci (ten sam router / Wi-Fi).
> Raspberry Pi OS domyślnie nie ma włączonej zapory, więc port 5000 jest dostępny.
> Jeśli masz włączony `ufw`, otwórz port: `sudo ufw allow 5000`.

---

## Krok 6 — Autostart przy włączeniu Raspberry Pi (systemd)

Dzięki temu aplikacja sama wystartuje po włączeniu/restarcie Pi i będzie się
restartować, gdyby padła.

### 6.1 Dopasuj plik usługi

W repozytorium jest gotowy plik `deploy/filamenty.service`. Domyślnie zakłada
użytkownika `pi` i katalog `/home/pi/tunia`. Jeśli Twój użytkownik lub ścieżka są
inne, sprawdź je:

```bash
whoami    # nazwa użytkownika, np. pi
pwd       # ścieżka, gdy jesteś w ~/tunia, np. /home/pi/tunia
```

i w razie potrzeby popraw plik:

```bash
nano deploy/filamenty.service
```

Mają się zgadzać trzy linie (podmień `pi` i ścieżkę na swoje):

```ini
User=pi
WorkingDirectory=/home/pi/tunia
ExecStart=/home/pi/tunia/.venv/bin/waitress-serve --host=0.0.0.0 --port=5000 app:app
```

### 6.2 Zainstaluj i włącz usługę

```bash
sudo cp deploy/filamenty.service /etc/systemd/system/filamenty.service
sudo systemctl daemon-reload
sudo systemctl enable --now filamenty.service
```

### 6.3 Sprawdź, że działa

```bash
systemctl status filamenty.service      # powinno być "active (running)"
journalctl -u filamenty.service -f      # podgląd logów na żywo (Ctrl+C kończy)
```

Od teraz aplikacja działa zawsze — wejdź na `http://ADRES-IP-RASPBERRY:5000`.

---

## Aktualizacja aplikacji

Pełna, bezpieczna instrukcja aktualizacji (z kopią zapasową danych) jest w osobnym
pliku: **`AKTUALIZACJA-RaspberryPi.md`**. W skrócie:

```bash
cp ~/tunia/filaments.db ~/filaments-kopia-$(date +%F).db   # kopia danych
cd ~/tunia && git pull                                     # nowy kod
.venv/bin/pip install -r requirements.txt                  # zależności
sudo systemctl restart filamenty.service                   # restart
```

---

## Kopia zapasowa danych

Wszystkie dane (Twoje filamenty) są w jednym pliku **`filaments.db`** w katalogu
aplikacji. Kopia zapasowa = skopiowanie tego pliku w bezpieczne miejsce:

```bash
cp ~/tunia/filaments.db ~/filaments-kopia-$(date +%F).db
```

Przywrócenie = skopiowanie pliku z powrotem do `~/tunia/filaments.db`
(najlepiej przy zatrzymanej usłudze: `sudo systemctl stop filamenty.service`).

---

## Rozwiązywanie problemów

**„Address already in use" / port zajęty** — coś już używa portu 5000. Znajdź i
zatrzymaj proces albo zmień port (w komendzie `waitress-serve` i w pliku usługi):

```bash
sudo lsof -i :5000
```

**Nie widać aplikacji z innego urządzenia** — sprawdź, czy:
- urządzenia są w tej samej sieci,
- używasz właściwego IP z `hostname -I`,
- usługa działa: `systemctl status filamenty.service`,
- (jeśli używasz `ufw`) port jest otwarty: `sudo ufw allow 5000`.

**Usługa nie startuje** — zobacz logi z błędem:

```bash
journalctl -u filamenty.service -n 50 --no-pager
```

Najczęstsza przyczyna to złe ścieżki/użytkownik w `filamenty.service`
(Krok 6.1) — popraw, a potem `sudo systemctl daemon-reload && sudo systemctl restart filamenty.service`.

**`python3 -m venv` zgłasza błąd** — doinstaluj moduł: `sudo apt install -y python3-venv`.
