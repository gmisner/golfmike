from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# URL configuration for local PostgreSQL server
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",  # Use service name if running in Docker
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test connection
session = SessionLocal()
result = session.execute(text("SELECT 1"))
print(result.fetchone())
session.close()