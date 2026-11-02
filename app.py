
import os
import sqlite3
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    str(Path(__file__).with_name("dieseldonor.db"))
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'Другие комплектующие',
                article TEXT DEFAULT '',
                description TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                availability TEXT DEFAULT 'В наличии'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")

        if username and password:
            existing = conn.execute(
                "SELECT id FROM admins WHERE username = ?",
                (username,)
            ).fetchone()

            if not existing:
                conn.execute(
                    "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "ok", "app": "DieselDonor"}


@app.route("/api/products")
def products_api():
    with get_db() as conn:
        products = conn.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()

    return jsonify([dict(product) for product in products])


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM admins WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["admin_id"] = user["id"]
            return redirect(url_for("admin"))

        flash("Неверный логин или пароль")

    return render_template("login.html")


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@admin_required
def admin():
    with get_db() as conn:
        products = conn.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()

    return render_template("admin.html", products=products)


@app.route("/admin/add", methods=["POST"])
@admin_required
def add_product():
    name = request.form.get("name", "").strip()

    if not name:
        flash("Укажи название товара")
        return redirect(url_for("admin"))

    values = (
        name,
        request.form.get("category", "Другие комплектующие"),
        request.form.get("article", ""),
        request.form.get("description", ""),
        request.form.get("photo_url", ""),
        request.form.get("availability", "В наличии")
    )

    with get_db() as conn:
        conn.execute("""
            INSERT INTO products
            (name, category, article, description, photo_url, availability)
            VALUES (?, ?, ?, ?, ?, ?)
        """, values)

    flash("Товар добавлен")
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,)
        )

    flash("Товар удалён")
    return redirect(url_for("admin"))


init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
