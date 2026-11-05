from typing import List, Dict, Any, Optional
from src.config.settings import settings

ALL_DAY_NAMES = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота"
]

# Официальное расписание звонков КОГПОАУ КТКПП
SLOT_TIMES = {
    1: "08:00 - 09:20",
    2: "09:35 - 10:55",
    3: "11:25 - 12:45",
    4: "12:55 - 14:15",
    5: "14:25 - 15:45",
    6: "15:50 - 17:10",
    7: "17:15 - 18:35"
}


class TextScheduleFormatter:
    """
    Форматирует расписание в читаемый текст для мессенджеров (Telegram / MAX).
    Поддерживает:
    - Разделение по подгруппам (ПГ.1 и ПГ.2)
    - Чередование 1-я / 2-я неделя (отсчет с 1 сентября):
      1-я неделя — предмет подчеркнут (числитель)
      2-я неделя — предмет под чертой (знаменатель)
    """

    def __init__(self, dataset_dict: Optional[Dict[str, Any]] = None, days_count: int = settings.DAYS_PER_WEEK):
        self.days_count = days_count
        self.day_names = ALL_DAY_NAMES[:self.days_count]
        self.groups = {g["id"]: g["code"] for g in (dataset_dict.get("groups", []) if dataset_dict else [])}
        self.teachers = {t["id"]: t["short_name"] for t in (dataset_dict.get("teachers", []) if dataset_dict else [])}
        self.rooms = {r["id"]: r["number"] for r in (dataset_dict.get("rooms", []) if dataset_dict else [])}
        self.subjects = {s["id"]: s["short_name"] for s in (dataset_dict.get("subjects", []) if dataset_dict else [])}
        self.subgroups = {sg["id"]: sg["name"] for sg in (dataset_dict.get("subgroups", []) if dataset_dict else [])}

    def format_group_schedule(
        self,
        group_id: int,
        schedule_entries: List[Dict[str, Any]],
        subgroup_id: Optional[int] = None,
        week_filter: Optional[int] = None  # 1 (1-я неделя), 2 (2-я неделя) или None (обе недели)
    ) -> str:
        grp_code = self.groups.get(group_id, f"Группа #{group_id}")
        week_title = f" [{week_filter}-я неделя]" if week_filter else " [Все недели]"
        lines = [f"📅 **Расписание для группы {grp_code}**{week_title}\n"]

        grp_entries = [e for e in schedule_entries if e["group_id"] == group_id]
        if subgroup_id is not None:
            grp_entries = [
                e for e in grp_entries
                if e["lesson_type"] == "whole_group" or e["subgroup_id"] == subgroup_id
            ]

        # Фильтрация по номеру недели
        if week_filter is not None:
            grp_entries = [
                e for e in grp_entries
                if e.get("week_type", "all") in ("all", str(week_filter))
            ]

        for day_idx in range(self.days_count):
            day_entries = [e for e in grp_entries if e["day_of_week"] == day_idx]
            if not day_entries:
                continue

            day_entries.sort(key=lambda e: (e["slot_num"], e["subgroup_id"] or 0, e.get("week_type", "all")))
            lines.append(f"📌 **{self.day_names[day_idx]}**")

            slots_map: Dict[int, List[Dict[str, Any]]] = {}
            for e in day_entries:
                slots_map.setdefault(e["slot_num"], []).append(e)

            for slot_num in sorted(slots_map.keys()):
                time_range = SLOT_TIMES.get(slot_num, "")
                slot_items = slots_map[slot_num]

                for item in slot_items:
                    subj = self.subjects.get(item["subject_id"], "Предмет")
                    teacher = self.teachers.get(item["teacher_id"], "Преподаватель")
                    room = self.rooms.get(item["room_id"], "Кабинет")
                    l_type = item["lesson_type"]
                    w_type = item.get("week_type", "all")

                    week_badge = ""
                    if week_filter is None:
                        if w_type == "1":
                            week_badge = " *(1-я нед / <u>подчеркнуто</u>)*"
                        elif w_type == "2":
                            week_badge = " *(2-я нед / под чертой)*"

                    if l_type == "whole_group":
                        lines.append(f"  • **{slot_num} пара** ({time_range}): {subj} — {teacher} (каб. {room}){week_badge}")
                    else:
                        sg_name = self.subgroups.get(item["subgroup_id"], "ПГ")
                        lines.append(f"  • **{slot_num} пара** [{sg_name}] ({time_range}): {subj} — {teacher} (каб. {room}){week_badge}")

            lines.append("")

        return "\n".join(lines) if len(lines) > 1 else f"Расписание для {grp_code} пока не составлено."

    def format_teacher_schedule(
        self,
        teacher_id: int,
        schedule_entries: List[Dict[str, Any]],
        week_filter: Optional[int] = None
    ) -> str:
        teacher_name = self.teachers.get(teacher_id, f"Преподаватель #{teacher_id}")
        week_title = f" [{week_filter}-я неделя]" if week_filter else ""
        lines = [f"👨‍🏫 **Расписание преподавателя {teacher_name}**{week_title}\n"]

        t_entries = [e for e in schedule_entries if e["teacher_id"] == teacher_id]
        if week_filter is not None:
            t_entries = [
                e for e in t_entries
                if e.get("week_type", "all") in ("all", str(week_filter))
            ]

        if not t_entries:
            return f"У преподавателя {teacher_name} нет занятий в расписании."

        for day_idx in range(self.days_count):
            day_entries = [e for e in t_entries if e["day_of_week"] == day_idx]
            if not day_entries:
                continue

            day_entries.sort(key=lambda e: (e["slot_num"], e.get("week_type", "all")))
            lines.append(f"📌 **{self.day_names[day_idx]}**")

            for item in day_entries:
                slot_num = item["slot_num"]
                time_range = SLOT_TIMES.get(slot_num, "")
                subj = self.subjects.get(item["subject_id"], "Предмет")
                grp = self.groups.get(item["group_id"], "Группа")
                room = self.rooms.get(item["room_id"], "Кабинет")
                sg = f" ({self.subgroups.get(item['subgroup_id'])})" if item["subgroup_id"] else ""
                w_type = item.get("week_type", "all")

                week_badge = ""
                if week_filter is None:
                    if w_type == "1":
                        week_badge = " *(1-я нед)*"
                    elif w_type == "2":
                        week_badge = " *(2-я нед)*"

                lines.append(f"  • **{slot_num} пара** ({time_range}): {grp}{sg} — {subj} (каб. {room}){week_badge}")

            lines.append("")

        return "\n".join(lines)
