from db_config import engine
from sqlalchemy import text


def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Connection successful!")
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    test_connection()
