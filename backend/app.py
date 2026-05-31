from flask import Flask, request, jsonify
import psycopg2
import os
import time

app = Flask(__name__)

# Read DB config from environment variables (NEVER hardcode!)
DB_HOST = os.environ.get('DB_HOST', 'db')
DB_NAME = os.environ.get('DB_NAME', 'guestbook')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'changeme')

def get_db():
    """Connect to Postgres, retrying if it's not ready yet."""
    for attempt in range(10):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, dbname=DB_NAME,
                user=DB_USER, password=DB_PASS
            )
            return conn
        except psycopg2.OperationalError:
            print(f"DB not ready, retry {attempt+1}/10")
            time.sleep(2)
    raise Exception("Could not connect to database")

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route('/api/entries', methods=['GET'])
def list_entries():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, message, created_at FROM entries ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {'id': r[0], 'name': r[1], 'message': r[2], 'created_at': r[3].isoformat()}
        for r in rows
    ])

@app.route('/api/entries', methods=['POST'])
def add_entry():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO entries (name, message) VALUES (%s, %s)",
        (data['name'], data['message'])
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'status': 'ok'}), 201

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)

