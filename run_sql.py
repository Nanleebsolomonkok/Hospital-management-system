import mysql.connector
import os

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'HospitalManagement_STU001'),
    'port':     int(os.environ.get('DB_PORT', 3306)),
    'autocommit': True,
}
conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
with open('phase3_schema.sql', 'r') as f:
    queries = f.read().split(';')
    for q in queries:
        if q.strip():
            try:
                cur.execute(q)
                print(f"Executed: {q[:30]}...")
            except Exception as e:
                print(f"Error executing {q[:30]}... : {e}")

conn.close()
print("Success")
