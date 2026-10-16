import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


import psycopg

def get_connection():
    connection = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return connection


if __name__ == "__main__":
    try:
        with get_connection() as connection:
            print("Successfully connected to PostgreSQL!")

            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database();")
                result = cursor.fetchone()
                print("Connected database:", result[0])

    except psycopg.Error as error:
        print("Database connection failed:", error)