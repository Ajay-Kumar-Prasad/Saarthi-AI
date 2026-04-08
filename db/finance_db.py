import os
import psycopg2


def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", ""),
            dbname=os.getenv("DB_NAME", "postgres"),
        )
    except Exception:
        return None


def insert_expense(amount: float, category: str, description: str, date, user_id: str = None):
    conn = get_db_connection()
    if conn is None:
        return

    cur = conn.cursor()
    cur.execute(
        """INSERT INTO expenses (amount, category, description, date, user_id)
           VALUES (%s, %s, %s, %s, %s)""",
        (amount, category, description, date, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_expenses(user_id: str = None):
    conn = get_db_connection()
    if conn is None:
        return []

    cur = conn.cursor()
    if user_id:
        cur.execute(
            "SELECT amount, category, description, date FROM expenses WHERE user_id = %s ORDER BY date DESC",
            (user_id,),
        )
    else:
        cur.execute("SELECT amount, category, description, date FROM expenses ORDER BY date DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
