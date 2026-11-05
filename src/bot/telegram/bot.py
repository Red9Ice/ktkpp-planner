from typing import Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from src.bot.core.service import BotScheduleService
from src.config.settings import settings

from src.bot.core.date_utils import get_academic_week_info

bot_service = BotScheduleService()
dp = Dispatcher()


def get_subgroup_keyboard(group_code: str, week_filter: Optional[int] = None) -> InlineKeyboardMarkup:
    """Создает инлайн-клавиатуру: выбор недели чередования, выбор подгруппы и скачивание файлов."""
    kb = [
        [
            InlineKeyboardButton(text="🔹 1-я неделя", callback_data=f"week:{group_code}:1"),
            InlineKeyboardButton(text="🔸 2-я неделя", callback_data=f"week:{group_code}:2"),
            InlineKeyboardButton(text="📅 Обе недели", callback_data=f"week:{group_code}:all")
        ],
        [
            InlineKeyboardButton(text="ПГ 1", callback_data=f"sched:{group_code}:1"),
            InlineKeyboardButton(text="ПГ 2", callback_data=f"sched:{group_code}:2"),
            InlineKeyboardButton(text="Вся группа", callback_data=f"sched:{group_code}:all")
        ],
        [
            InlineKeyboardButton(text="📄 Скачать PDF", callback_data=f"pdf:{group_code}"),
            InlineKeyboardButton(text="📊 Скачать Excel", callback_data="excel:full")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start — вывод приветствия и списка доступных команд."""
    _, curr_week_type, curr_week_name = get_academic_week_info()
    welcome_text = (
        f"👋 **Добро пожаловать в систему расписания {settings.COLLEGE_NAME}!**\n"
        f"📌 **Сейчас идет:** {curr_week_name}\n\n"
        "Доступные команды:\n"
        "▫️ `/schedule <группа>` — расписание группы (например, `/schedule ИС-11` или `/schedule С-11 1`)\n"
        "▫️ `/teacher <фамилия>` — расписание преподавателя (например, `/teacher Иванов`)\n"
        "▫️ `/week` — узнать текущую учебную неделю (1-я или 2-я)\n"
        "▫️ `/bells` — расписание звонков и перемен\n"
        "▫️ `/excel` — скачать сводную таблицу расписания в Excel\n"
        "▫️ `/help` — справка по командам\n\n"
        "⚙️ **Для диспетчера (Администратор):**\n"
        "▫️ `/generate` — запустить расчет расписания в облаке (GitHub Actions)\n"
        "▫️ `/substitute` — управление заменами"
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@dp.message(Command("week"))
async def cmd_week(message: types.Message):
    """Выводит текущую учебную неделю с отсчетом от 1 сентября."""
    abs_week, week_type, week_name = get_academic_week_info()
    explanation = (
        f"📅 **Текущая учебная неделя:** №{abs_week} — **{week_type}-я неделя**\n\n"
        f"• **1-я неделя:** в расписании предметы **подчеркнуты** <u>снизу</u>.\n"
        f"• **2-я неделя:** в расписании предметы расположены **под чертой**."
    )
    await message.answer(explanation, parse_mode="Markdown")


@dp.message(Command("bells"))
async def cmd_bells(message: types.Message):
    """Выводит официальное расписание звонков КТКПП."""
    text = bot_service.get_bell_schedule_text()
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    """Обработчик команды /schedule — получение расписания группы."""
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.answer("⚠️ Пожалуйста, укажите группу. Пример: `/schedule ИС-11` или `/schedule ИС-11 1`", parse_mode="Markdown")
        return

    group_code = args[0]
    subgroup_num = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    # По умолчанию определяем текущую неделю по календарю (отсчет с 1 сентября)
    _, curr_week_type, _ = get_academic_week_info()

    text, grp = bot_service.get_group_schedule(group_code, subgroup_num=subgroup_num, week_filter=curr_week_type)
    if not grp:
        await message.answer(text)
        return

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_subgroup_keyboard(grp.code, week_filter=curr_week_type)
    )


@dp.callback_query(F.data.startswith("week:"))
async def callback_week_filter(query: types.CallbackQuery):
    """Переключение отображения: 1-я неделя, 2-я неделя или обе недели."""
    parts = query.data.split(":")
    group_code = parts[1]
    week_arg = parts[2]
    week_filter = int(week_arg) if week_arg.isdigit() else None

    text, grp = bot_service.get_group_schedule(group_code, week_filter=week_filter)
    if grp:
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_subgroup_keyboard(grp.code, week_filter=week_filter)
        )
    await query.answer()


@dp.callback_query(F.data.startswith("sched:"))
async def callback_schedule(query: types.CallbackQuery):
    """Обработка нажатия кнопок переключения подгрупп (ПГ 1, ПГ 2, Вся группа)."""
    parts = query.data.split(":")
    group_code = parts[1]
    subgroup_arg = parts[2]
    subgroup_num = int(subgroup_arg) if subgroup_arg.isdigit() else None

    text, grp = bot_service.get_group_schedule(group_code, subgroup_num=subgroup_num)
    if grp:
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_subgroup_keyboard(grp.code)
        )
    await query.answer()


@dp.callback_query(F.data.startswith("pdf:"))
async def callback_pdf(query: types.CallbackQuery):
    """Отправка PDF-файла расписания группы по нажатию инлайн-кнопки."""
    group_code = query.data.split(":")[1]
    _, grp = bot_service.get_group_schedule(group_code)
    if not grp:
        await query.answer("Группа не найдена", show_alert=True)
        return

    await query.answer("Генерирую PDF...")
    pdf_buffer = bot_service.export_group_pdf(grp.id)
    doc_file = BufferedInputFile(pdf_buffer.getvalue(), filename=f"Schedule_{grp.code}.pdf")
    await query.message.answer_document(doc_file, caption=f"📄 Расписание для {grp.code}")


@dp.callback_query(F.data == "excel:full")
async def callback_excel(query: types.CallbackQuery):
    """Отправка сводного Excel-файла по нажатию инлайн-кнопки."""
    await query.answer("Формирую Excel-файл...")
    excel_buffer = bot_service.export_excel_file()
    doc_file = BufferedInputFile(excel_buffer.getvalue(), filename="College_Timetable.xlsx")
    await query.message.answer_document(doc_file, caption="📊 Полное расписание колледжа")


@dp.message(Command("excel"))
async def cmd_excel(message: types.Message):
    """Обработчик команды /excel — отправка сводного Excel-расписания."""
    await message.answer("⏳ Формирую сводный Excel-файл...")
    excel_buffer = bot_service.export_excel_file()
    doc_file = BufferedInputFile(excel_buffer.getvalue(), filename="College_Timetable.xlsx")
    await message.answer_document(doc_file, caption="📊 Сводное расписание колледжа (.xlsx)")


@dp.message(Command("teacher"))
async def cmd_teacher(message: types.Message):
    """Обработчик команды /teacher — поиск расписания преподавателя."""
    args = message.text.split(maxsplit=1)[1:] if message.text else []
    if not args:
        await message.answer("⚠️ Укажите фамилию преподавателя. Пример: `/teacher Иванов`", parse_mode="Markdown")
        return

    text, _ = bot_service.get_teacher_schedule(args[0])
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("generate"))
async def cmd_generate(message: types.Message):
    """Обработчик команды диспетчера /generate — запуск вычислений в GitHub Actions."""
    # Проверка прав администратора
    if settings.TELEGRAM_ADMIN_IDS and message.from_user.id not in settings.TELEGRAM_ADMIN_IDS:
        await message.answer("⛔ У вас нет прав диспетчера для запуска генерации.")
        return

    await message.answer("🚀 Отправляю запрос на запуск Solver в облачный раннер (GitHub Actions)...")
    res = await bot_service.trigger_solver_github_actions()
    if res.get("success"):
        await message.answer("✅ Генератор запущен в GitHub Actions! После завершения расписание обновится в базе данных.")
    else:
        await message.answer(f"⚠️ {res.get('error')}")


def get_bot() -> Optional[Bot]:
    """Возвращает экземпляр бота aiogram, если настроен токен."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)
