import psycopg2
import os

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT", 5432),
        connect_timeout=10,
        sslmode='require'   # prevents hanging
    )

def insert_expense(amount, category, description, date):
    try:
        print("➡️ DB: Trying insert...")

        conn = get_db_connection()   # THIS was failing
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO expenses (amount, category, description, date)
            VALUES (%s, %s, %s, %s)
            """,
            (amount, category, description, date)
        )

        conn.commit()

        print("✅ DB: Insert success")

        cur.close()
        conn.close()

    except Exception as e:
        print("❌ DB Insert Failed:", e)