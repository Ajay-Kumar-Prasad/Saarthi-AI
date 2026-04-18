import asyncio
import asyncpg
import logging
from datetime import datetime, timedelta, timezone

# Optional logging setup if you're debugging failures
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Consistent demo user
USER_ID = '00000000-0000-0000-0000-000000000001'

async def seed_data():
    print("Connecting to local database (127.0.0.1:5433)...")
    try:
        # Use simple direct connect logic. Adjust credentials if necessary.
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=5433,
            user='postgres',
            password='Saarthi@25',
            database='saarthi'
        )
    except Exception as e:
        print(f"❌ Failed to connect to the database: {e}")
        return

    try:
        print("Starting mock data seeding for multi-agent domains...")
        now = datetime.now(timezone.utc)
        
        # ── HEALTH DOMAIN ───────────────────────────────────────────────
        for i in range(7):
            d = (now - timedelta(days=i)).date()
            steps = 6000 + i * 1000  # realistic variation: 6k to 12k
            cals = 2000 + i * 150
            mins = 45 + i * 10
            rhr = 60 + (i % 5)
            
            await conn.execute("""
                INSERT INTO health_daily_metrics 
                (user_id, date, total_steps, total_calories, active_minutes, resting_heart_rate)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, date) DO NOTHING
            """, USER_ID, d, steps, cals, mins, rhr)
            
        for i in range(5):
            d = (now - timedelta(days=i)).date()
            start = now - timedelta(days=i, hours=7)
            end = now - timedelta(days=i, hours=1)
            duration = 6 * 60 # 6 hours
            await conn.execute("""
                INSERT INTO health_sleep_logs
                (user_id, date, start_time, end_time, duration_minutes, sleep_stages)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, date) DO NOTHING
            """, USER_ID, d, start, end, duration, '{"deep": 120, "light": 200, "rem": 40}')
            
        activities = ["Running", "Walking", "Gym", "Running", "Walking"]
        for i in range(5):
            d = (now - timedelta(days=i)).date()
            start = now - timedelta(days=i, hours=15)
            end = start + timedelta(minutes=45)
            await conn.execute("""
                INSERT INTO health_activity_logs
                (user_id, date, activity_type, start_time, end_time, duration_minutes, calories_burned, steps, avg_heart_rate)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, start_time) DO NOTHING
            """, USER_ID, d, activities[i], start, end, 45, 350.0, 4000, 140.0)
            
        print("✅ Inserted health data")
        
        # ── FINANCE DOMAIN ──────────────────────────────────────────────
        categories = ["Food", "Travel", "Shopping"]
        for i in range(10):
            d = now - timedelta(days=i)
            # Randomized looking amounts (150, 400, 650, etc.)
            amt = 150.0 + (i * 250.0)
            if amt > 5000:
                amt = 4500.50
            cat = categories[i % 3]
            await conn.execute("""
                INSERT INTO expenses (user_id, amount, category, description, date)
                VALUES ($1, $2, $3, $4, $5)
            """, USER_ID, amt, cat, f"{cat} expense logic test", d)
            
        print("✅ Inserted finance data")

        # ── LEARNING DOMAIN ─────────────────────────────────────────────
        # Learning resources
        res1_id = '11111111-1111-1111-1111-111111111111'
        res2_id = '22222222-2222-2222-2222-222222222222'
        await conn.execute("""
            INSERT INTO learning_resources (id, user_id, title, resource_type, status, tags)
            VALUES 
            ($1, $2, $3, $4, $5, $6),
            ($7, $8, $9, $10, $11, $12)
            ON CONFLICT (id) DO NOTHING
        """, 
        res1_id, USER_ID, "Mastering FastAPI in Python", "course", "in_progress", ["python", "backend"],
        res2_id, USER_ID, "Advanced PostgreSQL Architecture", "book", "not_started", ["database", "sql"])

        # Study sessions
        for i in range(3):
            # Scheduled ahead
            sched_at = now + timedelta(days=i+1, hours=2)
            await conn.execute("""
                INSERT INTO study_sessions (user_id, resource_id, title, scheduled_at, duration_minutes)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, resource_id, scheduled_at) DO NOTHING
            """, USER_ID, res1_id, f"Study Block Phase {i+1}", sched_at, 60)

        # Study goals
        await conn.execute("""
            INSERT INTO study_goals (user_id, resource_id, title, weekly_hours_target)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT DO NOTHING
        """, USER_ID, res1_id, "Finish FastAPI coursework by month end", 5.0)

        # Flashcards
        for i in range(3):
            await conn.execute("""
                INSERT INTO flashcards (user_id, resource_id, question, answer, tags)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO NOTHING
            """, USER_ID, res1_id, f"Test Concept #{i+1}?", f"Answer snippet for concept {i+1}", ["testing"])

        print("✅ Inserted learning data")
        print("\n🎉 All mock seed data successfully loaded into AlloyDB!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
