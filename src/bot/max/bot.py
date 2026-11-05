import logging
from typing import Dict, Any, Optional
from src.bot.core.service import BotScheduleService
from src.config.settings import settings

logger = logging.getLogger(__name__)


class MaxBotAdapter:
    """
    Адаптер для интеграции с платформой MAX Messenger (maxapi / maxogram).
    Предоставляет интерфейс и команды, полностью идентичные Telegram-боту.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.MAX_BOT_TOKEN
        self.service = BotScheduleService()

    async def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка входящего вебхука с сообщением из MAX Messenger.
        """
        text = message_data.get("text", "").strip()
        chat_id = message_data.get("chat_id")
        user_id = message_data.get("user_id")

        if not text:
            return {"action": "none"}

        parts = text.split()
        command = parts[0].lower()

        if command in ("/start", "start", "/help", "помощь"):
            reply = (
                f"👋 Добро пожаловать в систему расписания {settings.COLLEGE_NAME} (MAX Bot)!\n\n"
                "Команды:\n"
                "▫️ /schedule <группа> [подгруппа] — расписание группы (например, /schedule ИС-11)\n"
                "▫️ /teacher <преподаватель> — расписание преподавателя\n"
                "▫️ /week — узнать текущую неделю (1-я или 2-я)\n"
                "▫️ /bells — расписание звонков и перемен\n"
                "▫️ /excel — скачать полное расписание\n"
            )
            return {"action": "send_text", "chat_id": chat_id, "text": reply}

        elif command in ("/week", "неделя"):
            from src.bot.core.date_utils import get_academic_week_info
            abs_week, week_type, week_name = get_academic_week_info()
            reply = (
                f"📅 Текущая учебная неделя: №{abs_week} ({week_type}-я неделя)\n"
                f"• 1-я неделя: предметы подчеркнуты снизу\n"
                f"• 2-я неделя: предметы под чертой"
            )
            return {"action": "send_text", "chat_id": chat_id, "text": reply}

        elif command in ("/bells", "звонки"):
            reply = self.service.get_bell_schedule_text()
            return {"action": "send_text", "chat_id": chat_id, "text": reply}

        elif command in ("/schedule", "расписание"):
            if len(parts) < 2:
                return {
                    "action": "send_text",
                    "chat_id": chat_id,
                    "text": "⚠️ Укажите группу. Пример: /schedule ИС-11"
                }
            group_code = parts[1]
            subgroup_num = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
            reply, _ = self.service.get_group_schedule(group_code, subgroup_num=subgroup_num)
            return {"action": "send_text", "chat_id": chat_id, "text": reply}

        elif command in ("/teacher", "преподаватель"):
            if len(parts) < 2:
                return {
                    "action": "send_text",
                    "chat_id": chat_id,
                    "text": "⚠️ Укажите преподавателя. Пример: /teacher Иванов"
                }
            reply, _ = self.service.get_teacher_schedule(" ".join(parts[1:]))
            return {"action": "send_text", "chat_id": chat_id, "text": reply}

        elif command in ("/excel", "эксель"):
            excel_bytes = self.service.export_excel_file()
            return {
                "action": "send_document",
                "chat_id": chat_id,
                "filename": "College_Timetable.xlsx",
                "bytes": excel_bytes.getvalue()
            }

        return {"action": "none"}
