import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys

def migrate():
    # 1. Настройки подключения
    DB_SQLITE = 'dieseldonor.db'
    DB_URL = os.environ.get('DATABASE_URL')

    if not DB_URL:
        print("❌ Ошибка: Переменная DATABASE_URL не найдена в окружении.")
        return

    # Проверка наличия SQLite файла
    if not os.path.exists(DB_SQLITE):
        print(f"❌ Ошибка: Файл {DB_SQLITE} не найден в текущей директории.")
        return

    print("🚀 Начинаем миграцию данных...")

    try:
        # Подключение к источнику (SQLite)
        conn_sqlite = sqlite3.connect(DB_SQLITE)
        conn_sqlite.row_factory = sqlite3.Row
        cursor_sqlite = conn_sqlite.cursor()

        # Подключение к назначению (PostgreSQL)
        conn_pg = psycopg2.connect(DB_URL)
        cursor_pg = conn_pg.cursor()

        # 2. Создание структуры таблиц в PostgreSQL
        print("🛠️ Создаем структуру таблиц...")
        
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER DEFAULT 0,
            category TEXT,
            brand TEXT,
            model TEXT,
            engine TEXT,
            body_type TEXT,
            part_number TEXT,
            cross_numbers TEXT,
            images TEXT,
            quantity_available INTEGER DEFAULT 0,
            quantity_reserved INTEGER DEFAULT 0,
            quantity_expected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            customer_name TEXT,
            customer_phone TEXT,
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER DEFAULT 1,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS diagram_schemes (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            image_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS diagram_points (
            id SERIAL PRIMARY KEY,
            scheme_id INTEGER REFERENCES diagram_schemes(id) ON DELETE CASCADE,
            x_coord REAL NOT NULL,
            y_coord REAL NOT NULL,
            label TEXT,
            product_id INTEGER REFERENCES products(id)
        );
        """
        cursor_pg.execute(create_tables_sql)
        conn_pg.commit()

        # 3. Перенос Администраторов
        print("👤 Переносим администраторов...")
        cursor_sqlite.execute("SELECT * FROM admins")
        admins = cursor_sqlite.fetchall()
        if admins:
            admin_values = [(a['username'], a['password_hash']) for a in admins]
            execute_values(cursor_pg, "INSERT INTO admins (username, password_hash) VALUES %s ON CONFLICT (username) DO NOTHING", admin_values)
            conn_pg.commit()

        # 4. Перенос Товаров
        print("📦 Переносим товары...")
        cursor_sqlite.execute("SELECT * FROM products")
        products = cursor_sqlite.fetchall()
        
        if products:
            product_values = []
            for p in products:
                # Приводим данные к формату новой таблицы
                product_values.append((
                    p['name'],
                    p.get('description'),
                    p.get('price', 0),
                    p.get('category'),
                    p.get('brand'),
                    p.get('model'),
                    p.get('engine'),
                    p.get('body_type'),
                    p.get('part_number'),
                    p.get('cross_numbers'),
                    p.get('images'),
                    p.get('quantity_available', 0),
                    p.get('quantity_reserved', 0),
                    p.get('quantity_expected', 0),
                    p.get('created_at')
                ))
            
            execute_values(cursor_pg, """
                INSERT INTO products (name, description, price, category, brand, model, engine, body_type, part_number, cross_numbers, images, quantity_available, quantity_reserved, quantity_expected, created_at) 
                VALUES %s
            """, product_values)
            conn_pg.commit()

        # 5. Перенос Заказов (если есть)
        print("📝 Переносим заказы...")
        try:
            cursor_sqlite.execute("SELECT * FROM orders")
            orders = cursor_sqlite.fetchall()
            if orders:
                order_values = [(o['customer_name'], o['customer_phone'], o['product_id'], o['quantity'], o['status'], o['created_at']) for o in orders]
                execute_values(cursor_pg, "INSERT INTO orders (customer_name, customer_phone, product_id, quantity, status, created_at) VALUES %s", order_values)
                conn_pg.commit()
        except Exception as e:
            print(f"⚠️ При переносе заказов возникла ошибка (возможно, таблица пуста или отличается структура): {e}")

        print("✅ Миграция успешно завершена!")

    except Exception as e:
        print(f"❌ Критическая ошибка миграции: {e}")
    finally:
        if 'conn_sqlite' in locals(): conn_sqlite.close()
        if 'conn_pg' in locals(): conn_pg.close()

if __name__ == '__main__':
    migrate()
