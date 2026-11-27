"""CommerceIQ - Centralized MySQL and SQLAlchemy connection management."""

import os
from pathlib import Path
from typing import Optional

import mysql.connector
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

load_dotenv(PROJECT_ROOT / ".env")


def get_database_name() -> str:
    """Resolve target MySQL database name from environment or config.yaml."""
    env_name = os.getenv("DB_NAME")
    if env_name:
        return env_name
    if CONFIG_PATH.is_file():
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        db_cfg = cfg.get("database", {})
        if db_cfg.get("name"):
            return str(db_cfg["name"])
    return "commerceiq"


def get_connection(database: Optional[str] = None):
    """Create a mysql.connector connection to the local MySQL server."""
    kwargs = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "use_unicode": True,
    }
    if database is not None:
        kwargs["database"] = database
    return mysql.connector.connect(**kwargs)


def get_sqlalchemy_engine(database: Optional[str] = None) -> Engine:
    """Create a SQLAlchemy engine for MySQL using mysqlconnector."""
    target_db = database if database is not None else get_database_name()
    url = URL.create(
        drivername="mysql+mysqlconnector",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=target_db or None,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, future=True)


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
