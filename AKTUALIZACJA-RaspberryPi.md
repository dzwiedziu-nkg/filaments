# Aktualizacja na Raspberry Pi — krok po kroku

Jak bezpiecznie wgrać nową wersję aplikacji **Posiadane filamenty** na Raspberry Pi,
nie tracąc danych (Twoich filamentów).

> ⚠️ **Najważniejsze:** Twoje dane są w pliku **`filaments.db`**. Aktualizacja
> dotyczy tylko kodu (`app.py`, `templates/…`). **Nigdy nie nadpisuj
> `filaments.db`** podczas aktualizacji — instrukcje poniżej go chronią.

---

## Krok 1 — Zrób kopię zapasową danych

Zawsze przed aktualizacją (na Raspberry Pi):

```bash
cp ~/tunia/filaments.db ~/filaments-kopia-$(date +%F).db
```

Gdyby coś poszło nie tak, wrócisz do tej kopii (patrz „Wycofanie zmian").

---

## Krok 2 — Wgraj nową wersję kodu

Wybierz metodę zależnie od tego, jak instalowałeś aplikację.

### Metoda A — Git (jeśli aplikacja była sklonowana z repozytorium)

```bash
cd ~/tunia
git pull
```

`filaments.db` jest w `.gitignore`, więc `git pull` **nie ruszy Twoich danych**.

> Jeśli `git pull` zgłosi konflikt z lokalnymi zmianami, które chcesz porzucić:
> `git fetch && git reset --hard origin/main` (uwaga: skasuje lokalne zmiany w kodzie,
> ale nie w `filaments.db`, bo ten plik jest ignorowany).

### Metoda B — Kopiowanie z komputera (rsync)

Na komputerze, gdzie masz nową wersję plików (podmień `pi` i adres IP). `rsync`
skopiuje tylko kod, **pomijając bazę danych, środowisko i pliki tymczasowe**:

```bash
rsync -av --delete \
  --exclude='.venv' \
  --exclude='filaments.db' \
  --exclude='__pycache__' \
  --exclude='.git' \
  /home/nkg/tunia/  pi@ADRES-IP-RASPBERRY:~/tunia/
```

### Metoda C — Ręczne skopiowanie wybranych plików (scp)

Jeśli wolisz bez `rsync` — skopiuj tylko zmienione pliki (nigdy `filaments.db`):

```bash
scp app.py            pi@ADRES-IP-RASPBERRY:~/tunia/
scp -r templates      pi@ADRES-IP-RASPBERRY:~/tunia/
scp requirements.txt  pi@ADRES-IP-RASPBERRY:~/tunia/
```

---

## Krok 3 — Doinstaluj zależności (jeśli się zmieniły)

Bezpiecznie uruchomić zawsze — gdy nic nowego nie doszło, nic się nie stanie:

```bash
cd ~/tunia
.venv/bin/pip install -r requirements.txt
```

---

## Krok 4 — Zrestartuj usługę

```bash
sudo systemctl restart filamenty.service
```

> **Baza danych aktualizuje się sama.** Przy starcie aplikacja automatycznie
> dodaje brakujące kolumny do `filaments.db` (np. kolor ramki dodany w nowszej
> wersji). Nie musisz nic robić ręcznie — wystarczy restart.

Jeśli uruchamiasz aplikację ręcznie (bez usługi systemd), po prostu zatrzymaj
`Ctrl + C` i odpal ponownie:

```bash
.venv/bin/waitress-serve --host=0.0.0.0 --port=5000 app:app
```

---

## Krok 5 — Sprawdź, że działa

```bash
systemctl status filamenty.service      # powinno być "active (running)"
```

Następnie otwórz aplikację w przeglądarce i odśwież stronę:

```
http://ADRES-IP-RASPBERRY:5000
```

> Jeśli widzisz starą wersję strony, zrób **twarde odświeżenie** (wyczyszczenie
> pamięci podręcznej): na telefonie pociągnij w dół / wyczyść cache, na komputerze
> `Ctrl + Shift + R`.

---

## Szybkie podsumowanie (Metoda Git)

```bash
cp ~/tunia/filaments.db ~/filaments-kopia-$(date +%F).db   # 1. kopia
cd ~/tunia && git pull                                     # 2. nowy kod
.venv/bin/pip install -r requirements.txt                  # 3. zależności
sudo systemctl restart filamenty.service                   # 4. restart
systemctl status filamenty.service                         # 5. sprawdzenie
```

---

## Wycofanie zmian (gdy nowa wersja sprawia problemy)

**Powrót do poprzedniej wersji kodu (Git):**

```bash
cd ~/tunia
git log --oneline           # znajdź poprzedni commit
git reset --hard POPRZEDNI-COMMIT
sudo systemctl restart filamenty.service
```

**Przywrócenie danych z kopii zapasowej:**

```bash
sudo systemctl stop filamenty.service
cp ~/filaments-kopia-RRRR-MM-DD.db ~/tunia/filaments.db
sudo systemctl start filamenty.service
```

---

## Rozwiązywanie problemów

**Usługa nie wstaje po aktualizacji** — sprawdź logi z błędem:

```bash
journalctl -u filamenty.service -n 50 --no-pager
```

**Brak modułu / błąd importu** — doinstaluj zależności (Krok 3) i zrestartuj.

**Widać starą stronę** — twarde odświeżenie przeglądarki (`Ctrl + Shift + R`).

**Coś poważnie się zepsuło** — wykonaj „Wycofanie zmian" powyżej (kod + dane).

> Pełna instalacja od zera: zobacz `INSTALACJA-RaspberryPi.md`.
