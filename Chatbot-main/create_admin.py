from werkzeug.security import generate_password_hash
import sqlite3

# Define the username and password you want to insert
username = 'admin'
password = 'iniadminUNDIP'
# Hash the password
hashed_password = generate_password_hash(password)

# Connect to the SQLite database
conn = sqlite3.connect("C:\\Chatbot\\database_chatbot.db")
cursor = conn.cursor()

# Create the admin table if it doesn't exist (run this once)
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL
)
""")

# Insert the username and hashed password into the admin table
cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (username, hashed_password))

# Commit and close the connection
conn.commit()
conn.close()

print("Admin password has been successfully hashed and stored!")
