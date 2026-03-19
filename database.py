# database.py — Smart Database: PostgreSQL + SQLite fallback

import os
import sqlite3
from config import Config

def get_db():
    """Get database connection — PostgreSQL if available, SQLite fallback."""
    db_url = Config.DATABASE_URL

    if db_url and db_url.startswith('postgres'):
        return _get_postgres(db_url)
    else:
        return _get_sqlite()


def _get_postgres(db_url):
    """PostgreSQL connection."""
    try:
        import psycopg2
        import psycopg2.extras
        # Fix for Render/Heroku URL format
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        return PostgresWrapper(conn)
    except Exception as e:
        print(f"[DB] PostgreSQL failed: {e} — falling back to SQLite")
        return _get_sqlite()


def _get_sqlite():
    """SQLite connection."""
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return SQLiteWrapper(conn)


class PostgresWrapper:
    """Wraps PostgreSQL connection to match SQLite interface."""
    def __init__(self, conn):
        self._conn = conn
        self._cur  = conn.cursor()
        self.db_type = 'postgresql'

    def execute(self, sql, params=None):
        # Convert SQLite ? placeholders to PostgreSQL %s
        sql = sql.replace('?', '%s')
        # Convert AUTOINCREMENT to SERIAL
        sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        self._cur.execute(sql, params or ())
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row and self._cur.description:
            return dict(zip([d[0] for d in self._cur.description], row))
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if rows and self._cur.description:
            cols = [d[0] for d in self._cur.description]
            return [dict(zip(cols, row)) for row in rows]
        return rows

    def commit(self):
        self._conn.commit()

    def close(self):
        self._cur.close()
        self._conn.close()

    def __getitem__(self, key):
        return self.fetchone()[key]

    def keys(self):
        if self._cur.description:
            return [d[0] for d in self._cur.description]
        return []


class SQLiteWrapper:
    """Wraps SQLite connection."""
    def __init__(self, conn):
        self._conn = conn
        self.db_type = 'sqlite'

    def execute(self, sql, params=None):
        if params:
            self._conn.execute(sql, params)
        else:
            self._conn.execute(sql)
        return CursorWrapper(self._conn, sql, params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


class CursorWrapper:
    def __init__(self, conn, sql, params):
        self._conn   = conn
        self._cursor = None
        try:
            if params:
                self._cursor = conn.execute(sql, params)
            else:
                self._cursor = conn.execute(sql)
        except Exception:
            pass

    def fetchone(self):
        if self._cursor:
            return self._cursor.fetchone()
        return None

    def fetchall(self):
        if self._cursor:
            return self._cursor.fetchall()
        return []


def init_db():
    """Initialize database tables."""
    conn = get_db()
    db_type = conn.db_type

    if db_type == 'postgresql':
        import psycopg2
        raw = conn._conn
        cur = raw.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id               SERIAL PRIMARY KEY,
                username         TEXT UNIQUE NOT NULL,
                password_hash    TEXT NOT NULL,
                role             TEXT NOT NULL,
                email            TEXT,
                phone            TEXT,
                assigned_machine TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensor_history (
                id          SERIAL PRIMARY KEY,
                machine_id  TEXT NOT NULL,
                temperature REAL,
                vibration   REAL,
                pressure    REAL,
                hours       REAL,
                fail_prob   REAL,
                health      REAL,
                timestamp   TEXT
            )
        """)

        raw.commit()

        # Seed default users
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        if count == 0:
            _seed_users_postgres(cur)
            raw.commit()
        cur.close()
        conn.close()

    else:
        # SQLite
        raw = conn._conn
        raw.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                username         TEXT UNIQUE NOT NULL,
                password_hash    TEXT NOT NULL,
                role             TEXT NOT NULL,
                email            TEXT,
                phone            TEXT,
                assigned_machine TEXT
            )
        """)
        raw.execute("""
            CREATE TABLE IF NOT EXISTS sensor_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id  TEXT NOT NULL,
                temperature REAL,
                vibration   REAL,
                pressure    REAL,
                hours       REAL,
                fail_prob   REAL,
                health      REAL,
                timestamp   TEXT
            )
        """)
        raw.commit()

        count = raw.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            _seed_users_sqlite(raw)
            raw.commit()
        conn.close()


def _seed_users_sqlite(conn):
    from werkzeug.security import generate_password_hash
    defaults = [
        ("admin",     "Admin@123",    "admin",    "n2766363@gmail.com", "9999999999", None),
        ("engineer1", "Engineer@123", "engineer", "n2766363@gmail.com", "8888888888", None),
        ("operator1", "Operator@123", "operator", "n2766363@gmail.com", "7777777777", "MCH-101"),
        ("manager1",  "Manager@123",  "manager",  "n2766363@gmail.com", "6666666666", None),
    ]
    for u, p, r, e, ph, m in defaults:
        conn.execute(
            "INSERT INTO users (username,password_hash,role,email,phone,assigned_machine) VALUES (?,?,?,?,?,?)",
            (u, generate_password_hash(p), r, e, ph, m)
        )


def _seed_users_postgres(cur):
    from werkzeug.security import generate_password_hash
    defaults = [
        ("admin",     "Admin@123",    "admin",    "n2766363@gmail.com", "9999999999", None),
        ("engineer1", "Engineer@123", "engineer", "n2766363@gmail.com", "8888888888", None),
        ("operator1", "Operator@123", "operator", "n2766363@gmail.com", "7777777777", "MCH-101"),
        ("manager1",  "Manager@123",  "manager",  "n2766363@gmail.com", "6666666666", None),
    ]
    for u, p, r, e, ph, m in defaults:
        cur.execute(
            "INSERT INTO users (username,password_hash,role,email,phone,assigned_machine) VALUES (%s,%s,%s,%s,%s,%s)",
            (u, generate_password_hash(p), r, e, ph, m)
        )


def save_sensor_reading(machine_id, reading, prediction):
    """Save sensor reading to database for historical tracking."""
    try:
        from datetime import datetime
        conn = get_db()
        if conn.db_type == 'postgresql':
            cur = conn._conn.cursor()
            cur.execute("""
                INSERT INTO sensor_history
                (machine_id,temperature,vibration,pressure,hours,fail_prob,health,timestamp)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (machine_id, reading['temperature'], reading['vibration'],
                  reading['pressure'], reading['operating_hours'],
                  prediction['failure_probability'], prediction['health_score'],
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn._conn.commit()
            cur.close()
        else:
            raw = conn._conn
            raw.execute("""
                INSERT INTO sensor_history
                (machine_id,temperature,vibration,pressure,hours,fail_prob,health,timestamp)
                VALUES (?,?,?,?,?,?,?,?)
            """, (machine_id, reading['temperature'], reading['vibration'],
                  reading['pressure'], reading['operating_hours'],
                  prediction['failure_probability'], prediction['health_score'],
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            raw.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Save reading error: {e}")
