from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Настройки конфигурации приложения и интеграций (актуализировано под КОГПОАУ КТКПП)."""

    # Параметры приложения
    APP_NAME: str = "KTKPP College Timetable Solver & Cloud Bots"
    COLLEGE_NAME: str = "КОГПОАУ КТКПП"
    DEBUG: bool = False

    # База данных (PostgreSQL в облаке Supabase / Neon или локальный SQLite)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/college_timetable"
    DB_ECHO: bool = False

    # Telegram-бот
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_IDS: list[int] = []

    # MAX-бот
    MAX_BOT_TOKEN: Optional[str] = None

    # Сервер вебхуков (Render.com / Koyeb)
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8000
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None

    # Интеграция с GitHub Actions (для запуска вычислений Solver по требованию)
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO: Optional[str] = "Red9Ice/ktkpp-planner"
    GITHUB_WORKFLOW_ID: str = "run_solver.yml"

    # Параметры математического решателя (Solver) для КТКПП:
    # В реальном расписании колледжа 5 учебных дней (Понедельник - Пятница) и 7 звонковых пар
    SOLVER_MAX_TIME_SECONDS: int = 600
    SOLVER_NUM_WORKERS: int = 8
    DAYS_PER_WEEK: int = 5             # 0=Понедельник .. 4=Пятница (5-дневная учебная неделя)
    SLOTS_PER_DAY: int = 6             # Основная сетка расписания (пары 1..6, резерв до 7)
    MAX_GYM_CONCURRENT_GROUPS: int = 3 # Вместимость спортзала (одновременно до 3 подгрупп/групп)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
