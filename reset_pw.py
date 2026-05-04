import sqlite3
import bcrypt

db_path = r"C:\Users\bahma\Downloads\base-juridique-app\output\lexavo.db"
conn = sqlite3.connect(db_path)

pw_hash = bcrypt.hashpw(b"test1234", bcrypt.gensalt()).decode()
conn.execute("UPDATE users SET password_hash=? WHERE email='test@lexavo.be'", (pw_hash,))
conn.commit()

row = conn.execute("SELECT email, name FROM users WHERE email='test@lexavo.be'").fetchone()
print("Updated:", row)
conn.close()
