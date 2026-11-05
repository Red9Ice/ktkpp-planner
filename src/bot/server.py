from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from aiogram import types
import logging

from src.config.settings import settings
from src.bot.telegram.bot import dp, get_bot
from src.bot.max.bot import MaxBotAdapter
from src.db.session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_adapter = MaxBotAdapter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом веб-сервера: инициализация БД и регистрация вебхуков."""
    # Инициализация таблиц базы данных
    init_db()

    # Регистрация вебхука в Telegram при наличии настроенного URL
    bot = get_bot()
    if bot and settings.WEBHOOK_URL:
        webhook_path = f"{settings.WEBHOOK_URL}/webhook/telegram"
        logger.info(f"Регистрация Telegram вебхука по адресу: {webhook_path}")
        await bot.set_webhook(
            url=webhook_path,
            secret_token=settings.WEBHOOK_SECRET,
            drop_pending_updates=True
        )

    yield

    # Корректное удаление вебхука при завершении работы сервиса
    if bot:
        logger.info("Удаление вебхука Telegram...")
        await bot.delete_webhook()
        await bot.session.close()


app = FastAPI(title="College Timetable Cloud Bots", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Эндпоинт проверки работоспособности для мониторинга Render.com / Koyeb."""
    return {"status": "ok", "service": "College Timetable Cloud Bots"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Эндпоинт приема входящих обновлений (Updates) от Telegram через вебхук."""
    bot = get_bot()
    if not bot:
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Валидация секретного токена вебхука (при наличии в настройках)
    if settings.WEBHOOK_SECRET:
        token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token_header != settings.WEBHOOK_SECRET:
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    update_data = await request.json()
    update = types.Update(**update_data)
    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}


@app.post("/webhook/max")
async def max_webhook(request: Request):
    """Эндпоинт приема сообщений от платформы MAX Messenger через вебхук."""
    payload = await request.json()
    response = await max_adapter.handle_message(payload)
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.bot.server:app", host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT, reload=settings.DEBUG)
