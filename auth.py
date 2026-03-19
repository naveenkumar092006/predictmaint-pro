# auth.py — Authentication using smart database layer

import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from config import Config


class User(UserMixin):
    def __init__(self, id, username, role, email, assigned_machine=None, phone=None):
        self.id               = id
        self.username         = username
        self.role             = role
        self.email            = email
        self.assigned_machine = assigned_machine
        self.phone            = phone or ''

    def can(self, permission):
        perms = {
            "admin":    ["view_all","manage_users","generate_reports","view_costs",
                         "view_failures","update_maintenance","view_assigned"],
            "engineer": ["view_failures","update_maintenance","view_all"],
            "operator": ["view_assigned"],
            "manager":  ["view_all","generate_reports","view_costs"],
        }
        return permission in perms.get(self.role, [])


def _row_to_user(row):
    if not row:
        return None
    if isinstance(row, dict):
        return User(row["id"], row["username"], row["role"],
                    row.get("email",""), row.get("assigned_machine"),
                    row.get("phone",""))
    # sqlite3.Row
    try:
        keys = row.keys()
        return User(row["id"], row["username"], row["role"],
                    row["email"] if "email" in keys else "",
                    row["assigned_machine"] if "assigned_machine" in keys else None,
                    row["phone"] if "phone" in keys else "")
    except:
        return None


def _get_raw():
    """Get raw underlying connection for direct queries."""
    from database import get_db
    db = get_db()
    return db


def init_db():
    from database import init_db as _init
    _init()


def get_user_by_id(user_id):
    from database import get_db
    db = get_db()
    try:
        if db.db_type == 'postgresql':
            cur = db._conn.cursor()
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            row = cur.fetchone()
            cur.close()
            db.close()
            if row:
                return User(row[0],row[1],row[3],row[4] or "",row[6],row[5] or "")
        else:
            import sqlite3
            db._conn.row_factory = sqlite3.Row
            row = db._conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            db.close()
            return _row_to_user(row)
    except Exception as e:
        print(f"[Auth] get_user_by_id error: {e}")
    return None


def get_user_by_username(username):
    from database import get_db
    db = get_db()
    try:
        if db.db_type == 'postgresql':
            cur = db._conn.cursor()
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            row = cur.fetchone()
            cur.close()
            db.close()
            return row
        else:
            import sqlite3
            db._conn.row_factory = sqlite3.Row
            row = db._conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            db.close()
            return row
    except Exception as e:
        print(f"[Auth] get_user_by_username error: {e}")
    return None


def verify_user(username, password):
    row = get_user_by_username(username)
    if not row:
        return None
    if isinstance(row, dict):
        ph = row.get("password_hash","")
        if check_password_hash(ph, password):
            return User(row["id"],row["username"],row["role"],
                        row.get("email",""),row.get("assigned_machine"),row.get("phone",""))
    else:
        try:
            ph = row["password_hash"]
            if check_password_hash(ph, password):
                return _row_to_user(row)
        except:
            # Tuple from psycopg2
            if len(row) >= 3 and check_password_hash(row[2], password):
                return User(row[0],row[1],row[3],
                            row[4] if len(row)>4 else "",
                            row[6] if len(row)>6 else None,
                            row[5] if len(row)>5 else "")
    return None


def get_all_users():
    from database import get_db
    db = get_db()
    try:
        if db.db_type == 'postgresql':
            cur = db._conn.cursor()
            cur.execute("SELECT id,username,role,email,phone,assigned_machine FROM users")
            rows = cur.fetchall()
            cur.close()
            db.close()
            if rows and cur.description:
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
            return []
        else:
            import sqlite3
            db._conn.row_factory = sqlite3.Row
            rows = db._conn.execute(
                "SELECT id,username,role,email,phone,assigned_machine FROM users"
            ).fetchall()
            db.close()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Auth] get_all_users error: {e}")
    return []


def create_user(username, password, role, email, assigned_machine=None, phone=None):
    from database import get_db
    db = get_db()
    try:
        ph = generate_password_hash(password)
        if db.db_type == 'postgresql':
            cur = db._conn.cursor()
            cur.execute(
                "INSERT INTO users (username,password_hash,role,email,phone,assigned_machine) VALUES (%s,%s,%s,%s,%s,%s)",
                (username, ph, role, email, phone or '', assigned_machine)
            )
            db._conn.commit()
            cur.close()
        else:
            db._conn.execute(
                "INSERT INTO users (username,password_hash,role,email,phone,assigned_machine) VALUES (?,?,?,?,?,?)",
                (username, ph, role, email, phone or '', assigned_machine)
            )
            db._conn.commit()
        db.close()
        return True, "User created successfully"
    except Exception as e:
        db.close()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False, "Username already exists"
        return False, str(e)


def delete_user(user_id):
    from database import get_db
    db = get_db()
    try:
        if db.db_type == 'postgresql':
            cur = db._conn.cursor()
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
            db._conn.commit()
            cur.close()
        else:
            db._conn.execute("DELETE FROM users WHERE id=?", (user_id,))
            db._conn.commit()
        db.close()
    except Exception as e:
        print(f"[Auth] delete_user error: {e}")
