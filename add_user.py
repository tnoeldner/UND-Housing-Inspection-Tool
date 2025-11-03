import psycopg2
import bcrypt
import getpass

# Update these with your Neon DB credentials
DB_CONFIG = {
    'dbname': 'neondb',
    'user': 'neondb_owner',
    'password': 'npg_DrSgJpKb3eh1',
    'host': 'ep-muddy-heart-a4ht7hiy-pooler.us-east-1.aws.neon.tech',
    'port': '5432'
}

def add_user(username, email, password, is_admin=False):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password_hash, email, is_admin) VALUES (%s, %s, %s, %s)",
                (username, password_hash, email, is_admin))
    conn.commit()
    cur.close()
    conn.close()
    print(f"User '{username}' added successfully.")

if __name__ == "__main__":
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = getpass.getpass("Enter password: ")
    admin_input = input("Is admin? (y/N): ").strip().lower()
    is_admin = admin_input == 'y'
    add_user(username, email, password, is_admin)
