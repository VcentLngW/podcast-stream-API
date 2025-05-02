import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
db_host = os.getenv("DB_HOST", "localhost")
db_port = int(os.getenv("DB_PORT", "3306"))
db_user = os.getenv("DB_USER", "myuser")
db_password = os.getenv("DB_PASSWORD", "mypassword")
db_name = os.getenv("DB_NAME", "fastapi_db")

# Connect to MySQL server (without specifying a database)
connection = pymysql.connect(
    host=db_host,
    port=db_port,
    user=db_user,
    password=db_password,
)

try:
    with connection.cursor() as cursor:
        # Check if database exists
        cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
        result = cursor.fetchone()
        
        if not result:
            print(f"Creating database: {db_name}")
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database {db_name} created successfully")
        else:
            print(f"Database {db_name} already exists")

    print(f"You can now update your .env file with these settings:")
    print(f"DB_HOST={db_host}")
    print(f"DB_PORT={db_port}")
    print(f"DB_USER={db_user}")
    print(f"DB_PASSWORD={db_password}")
    print(f"DB_NAME={db_name}")
    
finally:
    connection.close()

print("Database setup complete!")