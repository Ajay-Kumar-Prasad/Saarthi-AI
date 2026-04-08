# db/finance_db.py
from db.alloydb import get_db_connection

def insert_expense(amount: float, category: str, description: str, date, user_id: str = None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO expenses (amount, category, description, date, user_id)
           VALUES (%s, %s, %s, %s, %s)""",
        (amount, category, description, date, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_all_expenses(user_id: str = None):
    conn = get_db_connection()
    cur = conn.cursor()
    if user_id:
        cur.execute(
            "SELECT amount, category, description, date FROM expenses WHERE user_id = %s ORDER BY date DESC",
            (user_id,)
        )
    else:
        cur.execute("SELECT amount, category, description, date FROM expenses ORDER BY date DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows