import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
try:
    cur.execute("SELECT id, name, profile_picture FROM ppv_creator")
    rows = cur.fetchall()
    print('rows', len(rows))
    for r in rows:
        print(r)
finally:
    conn.close()
