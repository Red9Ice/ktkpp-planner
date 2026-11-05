import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config.settings import settings

# Определение URL подключения к базе данных
db_url = settings.DATABASE_URL
if not db_url or "postgres:postgres@localhost" in db_url:
    # Если облачный PostgreSQL еще не настроен, используем локальный файл SQLite для тестов
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "timetable.db"))
    db_url = f"sqlite:///{sqlite_path}"

# Для SQLite отключаем проверку потоков
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    echo=settings.DB_ECHO,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Генератор контекста сессии базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация всех таблиц базы данных."""
    from src.db.models import Base
    Base.metadata.create_all(bind=engine)
