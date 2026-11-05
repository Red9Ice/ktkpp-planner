import io
from typing import Optional, Tuple, Dict, Any, List
from src.db.session import SessionLocal
from src.db.models import Group, Subgroup, Teacher, Room, Subject, ScheduleEntry, Substitution
from src.exporters.text_exporter import TextScheduleFormatter
from src.exporters.excel_exporter import ExcelTimetableExporter
from src.exporters.pdf_exporter import PDFTimetableExporter
from src.bot.core.date_utils import get_academic_week_info
from src.config.settings import settings
import httpx


class BotScheduleService:
    """
    Единый сервис бизнес-логики, используемый Telegram и MAX ботами.
    Предоставляет методы получения расписания групп и преподавателей, экспорта файлов и вызова Solver'а.
    Поддерживает двухнедельное чередование (1-я / 2-я неделя с отсчетом от 1 сентября).
    """

    def _get_dataset_dict(self, db) -> Dict[str, Any]:
        """Формирует словарь со справочниками из БД для генерации расписания."""
        groups = [{"id": g.id, "code": g.code, "name": g.name, "course": g.course, "size": g.size} for g in db.query(Group).all()]
        subgroups = [{"id": sg.id, "group_id": sg.group_id, "subgroup_num": sg.subgroup_num, "name": sg.name, "size": sg.size} for sg in db.query(Subgroup).all()]
        teachers = [{"id": t.id, "full_name": t.full_name, "short_name": t.short_name} for t in db.query(Teacher).filter(Teacher.is_active == True).all()]
        rooms = [{"id": r.id, "number": r.number, "room_type": r.room_type, "capacity": r.capacity} for r in db.query(Room).filter(Room.is_active == True).all()]
        subjects = [{"id": s.id, "code": s.code, "name": s.name, "short_name": s.short_name} for s in db.query(Subject).all()]

        return {
            "groups": groups,
            "subgroups": subgroups,
            "teachers": teachers,
            "rooms": rooms,
            "subjects": subjects
        }

    def _get_entries_list(self, db) -> List[Dict[str, Any]]:
        """Загружает текущую базовую версию расписания из БД."""
        entries = db.query(ScheduleEntry).filter(ScheduleEntry.version_id == "base").all()
        return [
            {
                "id": e.id,
                "group_id": e.group_id,
                "subgroup_id": e.subgroup_id,
                "subject_id": e.subject_id,
                "teacher_id": e.teacher_id,
                "room_id": e.room_id,
                "day_of_week": e.day_of_week,
                "slot_num": e.slot_num,
                "week_type": getattr(e, "week_type", "all"),
                "lesson_type": "whole_group" if e.subgroup_id is None else "split"
            }
            for e in entries
        ]

    def get_group_schedule(
        self,
        group_code: str,
        subgroup_num: Optional[int] = None,
        week_filter: Optional[int] = None
    ) -> Tuple[str, Optional[Group]]:
        """Возвращает текстовое расписание для группы и объект группы с учетом типа недели."""
        with SessionLocal() as db:
            grp = db.query(Group).filter(Group.code.ilike(group_code.strip())).first()
            if not grp:
                return f"❌ Группа «{group_code}» не найдена в базе данных.", None

            dataset_dict = self._get_dataset_dict(db)
            entries = self._get_entries_list(db)

            subgroup_id = None
            if subgroup_num:
                sg = db.query(Subgroup).filter(
                    Subgroup.group_id == grp.id,
                    Subgroup.subgroup_num == subgroup_num
                ).first()
                if sg:
                    subgroup_id = sg.id

            formatter = TextScheduleFormatter(dataset_dict)
            text = formatter.format_group_schedule(grp.id, entries, subgroup_id=subgroup_id, week_filter=week_filter)
            return text, grp

    def get_teacher_schedule(
        self,
        query: str,
        week_filter: Optional[int] = None
    ) -> Tuple[str, Optional[Teacher]]:
        """Возвращает текстовое расписание для преподавателя по фрагменту ФИО."""
        with SessionLocal() as db:
            teacher = db.query(Teacher).filter(
                (Teacher.short_name.ilike(f"%{query.strip()}%")) |
                (Teacher.full_name.ilike(f"%{query.strip()}%"))
            ).first()

            if not teacher:
                return f"❌ Преподаватель «{query}» не найден.", None

            dataset_dict = self._get_dataset_dict(db)
            entries = self._get_entries_list(db)

            formatter = TextScheduleFormatter(dataset_dict)
            text = formatter.format_teacher_schedule(teacher.id, entries, week_filter=week_filter)
            return text, teacher

    def get_bell_schedule_text(self) -> str:
        """Возвращает официальное расписание звонков колледжа КТКПП с перерывами."""
        return (
            "🔔 **Официальное расписание звонков КОГПОАУ КТКПП:**\n\n"
            "▫️ **1 пара:** 08:00 – 09:20 *(перерыв 15 минут)*\n"
            "▫️ **2 пара:** 09:35 – 10:55 *(перерыв 30 минут — обед)*\n"
            "▫️ **3 пара:** 11:25 – 12:45 *(перерыв 10 минут)*\n"
            "▫️ **4 пара:** 12:55 – 14:15 *(перерыв 10 минут)*\n"
            "▫️ **5 пара:** 14:25 – 15:45 *(перерыв 5 минут)*\n"
            "▫️ **6 пара:** 15:50 – 17:10 *(перерыв 5 минут)*\n"
            "▫️ **7 пара:** 17:15 – 18:35"
        )

    def export_excel_file(self) -> io.BytesIO:
        """Экспорт полного расписания колледжа в файл Excel (.xlsx)."""
        with SessionLocal() as db:
            dataset_dict = self._get_dataset_dict(db)
            entries = self._get_entries_list(db)
            exporter = ExcelTimetableExporter(dataset_dict)
            return exporter.export(entries)

    def export_group_pdf(self, group_id: int) -> io.BytesIO:
        """Экспорт расписания одной группы в PDF-документ."""
        with SessionLocal() as db:
            dataset_dict = self._get_dataset_dict(db)
            entries = self._get_entries_list(db)
            exporter = PDFTimetableExporter(dataset_dict)
            return exporter.export_group_schedule(group_id, entries)

    async def trigger_solver_github_actions(self) -> Dict[str, Any]:
        """
        Запуск рабочего процесса в GitHub Actions для выполнения вычислений Solver в облаке.
        """
        if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO:
            return {
                "success": False,
                "error": "GITHUB_TOKEN или GITHUB_REPO не настроены в переменных окружения."
            }

        url = f"https://api.github.com/repos/{settings.GITHUB_REPO}/actions/workflows/{settings.GITHUB_WORKFLOW_ID}/dispatches"
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {"ref": "main"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (200, 204):
                return {"success": True, "message": "Задача запуска Solver успешно отправлена в GitHub Actions."}
            else:
                return {"success": False, "error": f"Ошибка GitHub API: {resp.status_code} {resp.text}"}
