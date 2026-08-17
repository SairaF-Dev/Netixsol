import sqlite3
import os

def setup_database():
    # Agar pehle se DB bani hui hai toh usay delete kar dein (fresh start ke liye)
    if os.path.exists("data/local_metrics.db"):
        os.remove("data/local_metrics.db")

    # SQLite DB banayein (ya connect karein)
    conn = sqlite3.connect("data/local_metrics.db")
    cursor = conn.cursor()

    # Ek table banayein jis mein server ki health metrics hongi
    cursor.execute('''
        CREATE TABLE server_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT,
            cpu_usage_percent INTEGER,
            memory_usage_percent INTEGER,
            active_db_connections INTEGER,
            max_db_connections INTEGER,
            status TEXT
        )
    ''')

    # Dummy Data Insert karein (Yeh wo data hai jo Agent dhoondega)
    # Dekhein ke User_Auth_API ka CPU 99% hai aur connections full hain!
    metrics_data = [
        ("Payment_Gateway", 45, 60, 150, 500, "Healthy"),
        ("User_Auth_API", 99, 85, 500, 500, "Critical"),  # <- Agent isay pakrayega
        ("Frontend_Dashboard", 30, 40, 50, 500, "Healthy")
    ]

    cursor.executemany('''
        INSERT INTO server_metrics 
        (service_name, cpu_usage_percent, memory_usage_percent, active_db_connections, max_db_connections, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', metrics_data)

    conn.commit()
    print("✅ Database 'data/local_metrics.db' created successfully with dummy metrics!")
    
    # Check karne ke liye data print karein
    cursor.execute("SELECT * FROM server_metrics")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    conn.close()

if __name__ == "__main__":
    setup_database()