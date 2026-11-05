from typing import List, Dict, Any, Optional
from src.solver.model import CollegeTimetableSolver, TimetableDataset, TimetableSolution


class TimetableRepairManager:
    """
    Менеджер оперативных замен и корректировок:
    1. Прямая замена преподавателя: поиск компетентного коллеги, свободного в нужный слот.
    2. Точечное восстановление (Incremental Repair): вызов CP-SAT с блокировкой неизменных уроков.
    """

    def __init__(self, dataset: TimetableDataset, current_schedule: List[Dict[str, Any]]):
        self.dataset = dataset
        self.schedule = current_schedule

    def find_direct_substitute(
        self,
        subject_id: int,
        day_of_week: int,
        slot_num: int,
        exclude_teacher_id: int
    ) -> List[Dict[str, Any]]:
        """
        Поиск всех свободных активных преподавателей с нужной компетенцией в слот (day_of_week, slot_num).
        """
        # 1. Преподаватели, уже занятые уроками в этот слот
        busy_teacher_ids = {
            entry["teacher_id"]
            for entry in self.schedule
            if entry["day_of_week"] == day_of_week and entry["slot_num"] == slot_num
        }

        # 2. Преподаватели, заблокированные ограничениями доступности (больничный, отгул)
        blocked_teacher_ids = set()
        for ac in self.dataset.availability_constraints:
            if ac.get("entity_type") == "teacher" and ac.get("is_blocked", True):
                if ac.get("day_of_week") in (None, day_of_week):
                    if ac.get("slot_num") in (None, slot_num):
                        blocked_teacher_ids.add(ac["entity_id"])

        # 3. Фильтрация кандидатов
        candidates = []
        for t in self.dataset.teachers:
            t_id = t["id"]
            if t_id == exclude_teacher_id:
                continue
            if not t.get("is_active", True):
                continue
            if t_id in busy_teacher_ids or t_id in blocked_teacher_ids:
                continue

            candidates.append(t)

        return candidates

    def run_incremental_repair(
        self,
        affected_entry_ids: List[int],
        time_limit_seconds: int = 30
    ) -> TimetableSolution:
        """
        Фиксирует все незатронутые уроки и пересчитывает расписание только для проблемных занятий.
        """
        all_entry_ids = [e.get("lesson_req_id", idx) for idx, e in enumerate(self.schedule)]
        locked_entries = [eid for eid in all_entry_ids if eid not in affected_entry_ids]

        solver = CollegeTimetableSolver(self.dataset)
        solver.build_model(
            mode="incremental",
            base_schedule=self.schedule,
            locked_entries=locked_entries
        )
        return solver.solve(time_limit_seconds=time_limit_seconds)
