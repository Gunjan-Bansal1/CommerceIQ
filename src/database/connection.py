import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# Locate the project root and load environment variables
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    """Create a connection to the local MySQL server."""

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


if __name__ == "__main__":

    connection = None
    cursor = None

    try:
        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute("SELECT VERSION();")

        version = cursor.fetchone()[0]

        print("MySQL connection successful.")
        print(f"MySQL Server Version: {version}")

    except mysql.connector.Error as error:
        print(f"MySQL connection failed: {error}")
        raise SystemExit(1)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            print("MySQL connection closed.")