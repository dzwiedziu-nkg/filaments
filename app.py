#!/usr/bin/env python3
"""Posiadane filamenty — prosta aplikacja webowa do śledzenia filamentów do druku 3D.

Backend: Flask + SQLite (jeden plik bazy, bez osobnego serwera bazodanowego).
Idealne na domowy serwer / Raspberry Pi.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "filaments.db"

# Próg, poniżej którego wiersz zostaje podświetlony (w gramach).
LOW_STOCK_THRESHOLD = 300

app = Flask(__name__)
# Zmiany w szablonie HTML widoczne po odświeżeniu strony, bez restartu serwera.
app.config["TEMPLATES_AUTO_RELOAD"] = True


# --------------------------------------------------------------------------- #
#  Baza danych
# --------------------------------------------------------------------------- #
def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


@app.teardown_appcontext
def close_db(_exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def init_db():
    """Tworzy tabele przy pierwszym uruchomieniu."""
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS filaments (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            type           TEXT NOT NULL DEFAULT 'PLA',
            color          TEXT NOT NULL DEFAULT '',
            color_hex      TEXT NOT NULL DEFAULT '#cccccc',
            weight_initial REAL NOT NULL DEFAULT 0,
            weight_current REAL NOT NULL DEFAULT 0,
            purchase_date  TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filament_id INTEGER NOT NULL,
            amount      REAL NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (filament_id) REFERENCES filaments(id) ON DELETE CASCADE
        );
        """
    )
    # Migracja: dodaj kolumnę color_hex do istniejących baz (sprzed tej wersji).
    cols = [r[1] for r in db.execute("PRAGMA table_info(filaments)").fetchall()]
    if "color_hex" not in cols:
        db.execute("ALTER TABLE filaments ADD COLUMN color_hex TEXT NOT NULL DEFAULT '#cccccc'")
    db.commit()
    db.close()


def serialize(row, can_undo):
    return {
        "id": row["id"],
        "type": row["type"],
        "color": row["color"],
        "color_hex": row["color_hex"],
        "weight_initial": row["weight_initial"],
        "weight_current": row["weight_current"],
        "purchase_date": row["purchase_date"],
        "can_undo": can_undo,
    }


def fetch_one(db, fid):
    row = db.execute(
        """
        SELECT f.*,
               (SELECT COUNT(*) FROM usage_log u WHERE u.filament_id = f.id) AS undo_count
        FROM filaments f WHERE f.id = ?
        """,
        (fid,),
    ).fetchone()
    if row is None:
        return None
    return serialize(row, row["undo_count"] > 0)


# --------------------------------------------------------------------------- #
#  Widok
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html", threshold=LOW_STOCK_THRESHOLD)


# --------------------------------------------------------------------------- #
#  API
# --------------------------------------------------------------------------- #
@app.route("/api/filaments")
def list_filaments():
    db = get_db()
    rows = db.execute(
        """
        SELECT f.*,
               (SELECT COUNT(*) FROM usage_log u WHERE u.filament_id = f.id) AS undo_count
        FROM filaments f
        ORDER BY f.purchase_date ASC, f.id ASC
        """
    ).fetchall()
    return jsonify([serialize(r, r["undo_count"] > 0) for r in rows])


@app.route("/api/filaments", methods=["POST"])
def create_filament():
    data = request.get_json(force=True) or {}
    initial = _to_float(data.get("weight_initial"))
    # "Gramatura teraz" startowo równa się gramaturze po zakupie,
    # chyba że użytkownik poda inną (np. napoczęta szpula).
    current = data.get("weight_current")
    current = initial if current in (None, "") else _to_float(current)

    db = get_db()
    cur = db.execute(
        """INSERT INTO filaments (type, color, color_hex, weight_initial, weight_current, purchase_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            (data.get("type") or "PLA").strip(),
            (data.get("color") or "").strip(),
            (data.get("color_hex") or "#cccccc").strip(),
            initial,
            current,
            (data.get("purchase_date") or "").strip(),
        ),
    )
    db.commit()
    return jsonify(fetch_one(db, cur.lastrowid)), 201


@app.route("/api/filaments/<int:fid>", methods=["PUT"])
def update_filament(fid):
    data = request.get_json(force=True) or {}
    allowed = ("type", "color", "color_hex", "weight_initial", "weight_current", "purchase_date")
    fields, values = [], []
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            value = data[key]
            if key in ("weight_initial", "weight_current"):
                value = _to_float(value)
            elif isinstance(value, str):
                value = value.strip()
            values.append(value)
    if not fields:
        return jsonify({"error": "brak pól do aktualizacji"}), 400

    db = get_db()
    values.append(fid)
    db.execute(f"UPDATE filaments SET {', '.join(fields)} WHERE id = ?", values)
    db.commit()
    result = fetch_one(db, fid)
    if result is None:
        return jsonify({"error": "nie znaleziono"}), 404
    return jsonify(result)


@app.route("/api/filaments/<int:fid>", methods=["DELETE"])
def delete_filament(fid):
    db = get_db()
    db.execute("DELETE FROM filaments WHERE id = ?", (fid,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/filaments/<int:fid>/use", methods=["POST"])
def use_filament(fid):
    """Odejmuje zużytą ilość gramów od stanu i zapisuje to w historii (do cofnięcia)."""
    data = request.get_json(force=True) or {}
    amount = _to_float(data.get("amount"))
    if amount <= 0:
        return jsonify({"error": "ilość musi być większa od zera"}), 400

    db = get_db()
    row = db.execute("SELECT weight_current FROM filaments WHERE id = ?", (fid,)).fetchone()
    if row is None:
        return jsonify({"error": "nie znaleziono"}), 404

    db.execute(
        "UPDATE filaments SET weight_current = weight_current - ? WHERE id = ?",
        (amount, fid),
    )
    db.execute(
        "INSERT INTO usage_log (filament_id, amount, created_at) VALUES (?, ?, ?)",
        (fid, amount, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return jsonify(fetch_one(db, fid))


@app.route("/api/filaments/<int:fid>/undo", methods=["POST"])
def undo_filament(fid):
    """Cofa ostatnie odjęcie — przywraca gramy i usuwa wpis z historii."""
    db = get_db()
    log = db.execute(
        "SELECT id, amount FROM usage_log WHERE filament_id = ? ORDER BY id DESC LIMIT 1",
        (fid,),
    ).fetchone()
    if log is None:
        return jsonify({"error": "nie ma czego cofać"}), 400

    db.execute(
        "UPDATE filaments SET weight_current = weight_current + ? WHERE id = ?",
        (log["amount"], fid),
    )
    db.execute("DELETE FROM usage_log WHERE id = ?", (log["id"],))
    db.commit()
    return jsonify(fetch_one(db, fid))


def _to_float(value):
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return 0.0


# Uruchamiane także przy imporcie (np. przez waitress-serve app:app),
# dzięki czemu baza istnieje niezależnie od sposobu startu.
init_db()


if __name__ == "__main__":
    # host=0.0.0.0 → dostępne z innych urządzeń w sieci domowej (telefon, laptop).
    app.run(host="0.0.0.0", port=5000, threaded=True)
