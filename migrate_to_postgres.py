import os
import csv
import psycopg2
from psycopg2.extras import execute_values

def get_db_url():
    """Получает URL базы данных из переменной окружения или файла"""
    url = os.environ.get('DATABASE_URL')
    if not url:
        try:
            with open('db_url.txt', 'r') as f:
                url = f.read().strip()
        except FileNotFoundError:
            pass
    return url

def migrate_csv_to_pg(csv_path, db_url):
    print(f"🚀 Начинаем миграцию из {csv_path}...")
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Создаем таблицы
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()

    # Читаем CSV и переносим
    count = 0
    # ВАЖНО: encoding='cp1251' для русской кодировки Windows
    with open(csv_path, 'r', encoding='cp1251') as f:
        reader = csv.DictReader(f, delimiter=';')
        batch = []
        
        for row in reader:
            # Маппинг полей из твоего CSV в базу
            item = (
                row.get('Наименование'),
                row.get('Комментарий'),
                int(float(row.get('Цена', 0) or 0)),
                row.get('Запчасть'),
                row.get('Марка'),
                row.get('Модель'),
                row.get('Двигатель'),
                row.get('Кузов'),
                row.get('Номер производителя'),
                row.get('Кросс-номера'),
                row.get('Превью'),
                int(float(row.get('DieselDonor (свободно)', 0) or 0))
            )
            batch.append(item)
            
            # Вставляем пачками по 100 штук для скорости
            if len(batch) >= 100:
                execute_values(cur, """
                    INSERT INTO products (name, description, price, category, brand, model, engine, body_type, part_number, cross_numbers, images, quantity_available) 
                    VALUES %s
                """, batch)
                conn.commit()
                count += len(batch)
                print(f"   ⏳ Перенесено {count} товаров...")
                batch = []

        # Доinsert остаток
        if batch:
            execute_values(cur, """
                INSERT INTO products (name, description, price, category, brand, model, engine, body_type, part_number, cross_numbers, images, quantity_available) 
                VALUES %s
            """, batch)
            conn.commit()
            count += len(batch)

    print(f"✅ Миграция завершена! Всего перенесено: {count} товаров.")
    conn.close()

if __name__ == '__main__':
    DB_URL = get_db_url()
    if not DB_URL:
        print("❌ Ошибка: Не найден DATABASE_URL. Создай файл db_url.txt или задай переменную окружения.")
    else:
        migrate_csv_to_pg('catalog_03-11-26_10-28.csv', DB_URL)