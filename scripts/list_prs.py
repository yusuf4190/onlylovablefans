import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
try:
    cur.execute("SELECT id, request_slug, status, created_at, approved_at, expiry_at, fan_email FROM ppv_paymentrequest ORDER BY created_at DESC LIMIT 10")
    rows = cur.fetchall()
    print('found', len(rows))
    for r in rows:
        print(r)
finally:
    conn.close()
