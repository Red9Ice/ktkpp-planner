import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from ortools.sat.python import cp_model
from src.solver.contiguity import add_subgroup_contiguity_and_start_constraints


@dataclass
class LessonRequirement:
    """Требование к проведению одного конкретного занятия."""
    id: int
    group_id: int
    subject_id: int
    teacher_id: int
    lesson_type: str  # 'whole_group' (вся группа) или 'split' (по подгруппам)
    subgroup_id: Optional[int]  # None для whole_group, либо ID конкретной подгруппы
    week_type: str = "all"      # 'all' (каждую неделю), '1' (1-я неделя / подчеркнутая), '2' (2-я неделя / под чертой)
    preferred_room_id: Optional[int] = None
    required_room_type: str = "any"
    subgroup_size: int = 25
    fixed_day: Optional[int] = None   # Фиксированный день (например, 0 для Разговоров о важном)
    fixed_slot: Optional[int] = None  # Фиксированная пара (например, 1 для Разговоров о важном)


@dataclass
class TimetableDataset:
    """Набор входных данных для решателя расписания КТКПП."""
    groups: List[Dict[str, Any]]
    subgroups: List[Dict[str, Any]]
    teachers: List[Dict[str, Any]]
    rooms: List[Dict[str, Any]]
    subjects: List[Dict[str, Any]]
    curriculum_workload: List[Dict[str, Any]]
    availability_constraints: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TimetableSolution:
    """Результат работы решателя расписания."""
    status: str
    objective_value: float
    wall_time_seconds: float
    entries: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class CollegeTimetableSolver:
    """
    Математический решатель расписания колледжа КТКПП на базе Google OR-Tools CP-SAT.
    Учитывает:
    - Двухнедельное чередование: 1-я неделя (подчеркнутая) / 2-я неделя (под чертой) / каждую неделю
    - 5-дневную учебную неделю (Понедельник - Пятница)
    - Подгруппы (ПГ.1 и ПГ.2) и синхронизацию общих лекций
    - Непрерывность учебного дня подгруппы через AddAutomaton для каждой недели отдельно
    - Старт дня не позже 3-й пары (start <= 3)
    - Мягкий штраф за 6-ю пару
    - Вместимость спортзала (С/з) для одновременных занятий нескольких групп
    - Фиксированные слоты (Разговоры о важном / Классный час на 1 паре понедельника)
    """

    def __init__(
        self,
        dataset: TimetableDataset,
        days_per_week: int = 5,      # 5 дней (Понедельник - Пятница)
        slots_per_day: int = 6,      # от 1 до 6 пар в день
        max_start_slot: int = 3,     # Старт дня <= 3
        max_lessons_per_day: int = 5,
        max_gym_capacity: int = 3,   # Максимум групп/подгрупп одновременно в спортзале (С/з)
        num_workers: int = 8
    ):
        self.dataset = dataset
        self.days_per_week = days_per_week
        self.slots_per_day = slots_per_day
        self.max_start_slot = max_start_slot
        self.max_lessons_per_day = max_lessons_per_day
        self.max_gym_capacity = max_gym_capacity
        self.num_workers = num_workers

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Индексы для быстрого поиска
        self.subgroups_by_group: Dict[int, List[int]] = {}
        for sg in dataset.subgroups:
            self.subgroups_by_group.setdefault(sg["group_id"], []).append(sg["id"])

        self.rooms_by_id = {r["id"]: r for r in dataset.rooms}
        self.subjects_by_id = {s["id"]: s for s in dataset.subjects}
        self.teachers_by_id = {t["id"]: t for t in dataset.teachers}

        # Сформированные требования к занятиям
        self.lesson_reqs: List[LessonRequirement] = []
        self._generate_lesson_requirements()

    def _generate_lesson_requirements(self):
        """Разворачивает нагрузку в отдельные требования с учетом типа недели (all, 1, 2)."""
        req_id = 1
        for wl in self.dataset.curriculum_workload:
            subject = self.subjects_by_id[wl["subject_id"]]
            req_room_type = subject.get("required_room_type", "any")
            pairs_count = wl["pairs_per_week"]
            group_id = wl["group_id"]
            teacher_id = wl["teacher_id"]
            l_type = wl["lesson_type"]
            w_type = wl.get("week_type", "all")
            pref_room = wl.get("preferred_room_id")

            # Фиксированные слоты воспитательного блока
            fixed_day = wl.get("fixed_day")
            fixed_slot = wl.get("fixed_slot")
            subj_name = subject.get("name", "").lower()
            if "разговоры о важном" in subj_name:
                fixed_day = 0
                fixed_slot = 1
            elif "классный час" in subj_name:
                fixed_day = 0
                fixed_slot = 1

            if l_type == "whole_group":
                for _ in range(pairs_count):
                    self.lesson_reqs.append(
                        LessonRequirement(
                            id=req_id,
                            group_id=group_id,
                            subject_id=subject["id"],
                            teacher_id=teacher_id,
                            lesson_type="whole_group",
                            subgroup_id=None,
                            week_type=w_type,
                            preferred_room_id=pref_room,
                            required_room_type=req_room_type,
                            subgroup_size=next((g["size"] for g in self.dataset.groups if g["id"] == group_id), 25),
                            fixed_day=fixed_day,
                            fixed_slot=fixed_slot
                        )
                    )
                    req_id += 1
            else:
                subgroup_ids = self.subgroups_by_group.get(group_id, [])
                for sg_id in subgroup_ids:
                    sg_size = next((sg["size"] for sg in self.dataset.subgroups if sg["id"] == sg_id), 13)
                    for _ in range(pairs_count):
                        self.lesson_reqs.append(
                            LessonRequirement(
                                id=req_id,
                                group_id=group_id,
                                subject_id=subject["id"],
                                teacher_id=teacher_id,
                                lesson_type="split",
                                subgroup_id=sg_id,
                                week_type=w_type,
                                preferred_room_id=pref_room,
                                required_room_type=req_room_type,
                                subgroup_size=sg_size,
                                fixed_day=fixed_day,
                                fixed_slot=fixed_slot
                            )
                        )
                        req_id += 1

    def build_model(
        self,
        mode: str = "full",
        base_schedule: Optional[List[Dict[str, Any]]] = None,
        locked_entries: Optional[List[int]] = None
    ):
        """Построение модели CP-SAT с двухнедельным чередованием."""
        self.model = cp_model.CpModel()
        objective_terms = []

        # Переменные решения: x[req_id, day, slot, room_id] in {0, 1}
        self.x: Dict[Tuple[int, int, int, int], cp_model.IntVar] = {}

        # Предварительный отбор подходящих кабинетов
        suitable_rooms: Dict[int, List[int]] = {}
        for req in self.lesson_reqs:
            s_rooms = []
            for r in self.dataset.rooms:
                if not r.get("is_active", True):
                    continue
                if req.required_room_type != "any" and r["room_type"] != req.required_room_type:
                    continue
                if r["room_type"] != "gym" and r["capacity"] < req.subgroup_size:
                    continue
                s_rooms.append(r["id"])

            if not s_rooms:
                s_rooms = [r["id"] for r in self.dataset.rooms if r.get("is_active", True)]
            suitable_rooms[req.id] = s_rooms

        # 1. Создание переменных и выбор слота
        for req in self.lesson_reqs:
            req_vars = []
            for d in range(self.days_per_week):
                for s in range(1, self.slots_per_day + 1):
                    if req.fixed_day is not None and d != req.fixed_day:
                        continue
                    if req.fixed_slot is not None and s != req.fixed_slot:
                        continue

                    for r_id in suitable_rooms[req.id]:
                        var = self.model.NewBoolVar(f"x_{req.id}_{d}_{s}_{r_id}")
                        self.x[(req.id, d, s, r_id)] = var
                        req_vars.append(var)

                        if s == 6:
                            objective_terms.append(20 * var)
                        if req.preferred_room_id and r_id == req.preferred_room_id:
                            objective_terms.append(-5 * var)

            self.model.AddExactlyOne(req_vars)

        # 2. Жёсткое ограничение: занятость преподавателя раздельно по 1-й и 2-й неделям
        for t in self.dataset.teachers:
            t_id = t["id"]
            for d in range(self.days_per_week):
                for s in range(1, self.slots_per_day + 1):
                    for active_week in ("1", "2"):
                        teacher_vars = []
                        for req in self.lesson_reqs:
                            if req.teacher_id == t_id and req.week_type in ("all", active_week):
                                for r_id in suitable_rooms[req.id]:
                                    if (req.id, d, s, r_id) in self.x:
                                        teacher_vars.append(self.x[(req.id, d, s, r_id)])
                        self.model.AddAtMostOne(teacher_vars)

        # 3. Жёсткое ограничение: занятость кабинетов раздельно по 1-й и 2-й неделям
        for r in self.dataset.rooms:
            r_id = r["id"]
            is_gym = (r.get("room_type") == "gym" or r.get("number") == "С/з")

            for d in range(self.days_per_week):
                for s in range(1, self.slots_per_day + 1):
                    for active_week in ("1", "2"):
                        room_vars = []
                        for req in self.lesson_reqs:
                            if req.week_type in ("all", active_week) and r_id in suitable_rooms[req.id]:
                                if (req.id, d, s, r_id) in self.x:
                                    room_vars.append(self.x[(req.id, d, s, r_id)])

                        if is_gym:
                            self.model.Add(sum(room_vars) <= self.max_gym_capacity)
                        else:
                            self.model.AddAtMostOne(room_vars)

        # 4. Жёсткое ограничение: посещаемость подгрупп и непрерывность дня на каждой неделе
        all_subgroups = self.dataset.subgroups

        for sg in all_subgroups:
            sg_id = sg["id"]
            grp_id = sg["group_id"]

            for d in range(self.days_per_week):
                for active_week in ("1", "2"):
                    daily_slot_vars = []
                    for s in range(1, self.slots_per_day + 1):
                        slot_vars = []
                        for req in self.lesson_reqs:
                            if req.group_id == grp_id and req.week_type in ("all", active_week):
                                if req.lesson_type == "whole_group" or req.subgroup_id == sg_id:
                                    for r_id in suitable_rooms[req.id]:
                                        if (req.id, d, s, r_id) in self.x:
                                            slot_vars.append(self.x[(req.id, d, s, r_id)])

                        self.model.AddAtMostOne(slot_vars)

                        slot_active = self.model.NewBoolVar(f"sg_{sg_id}_w{active_week}_{d}_{s}")
                        self.model.Add(slot_active == sum(slot_vars))
                        daily_slot_vars.append(slot_active)

                    self.model.Add(sum(daily_slot_vars) <= self.max_lessons_per_day)

                    # Контроль непрерывности и старта дня <= 3 для каждой недели
                    add_subgroup_contiguity_and_start_constraints(
                        self.model,
                        daily_slot_vars,
                        max_start_slot=self.max_start_slot
                    )

        # 5. Ограничения доступности
        for ac in self.dataset.availability_constraints:
            if not ac.get("is_blocked", True):
                continue
            e_type = ac["entity_type"]
            e_id = ac["entity_id"]
            ac_day = ac.get("day_of_week")
            ac_slot = ac.get("slot_num")

            days_to_block = [ac_day] if ac_day is not None else list(range(self.days_per_week))
            slots_to_block = [ac_slot] if ac_slot is not None else list(range(1, self.slots_per_day + 1))

            for d in days_to_block:
                if d >= self.days_per_week:
                    continue
                for s in slots_to_block:
                    for req in self.lesson_reqs:
                        should_block = False
                        if e_type == "teacher" and req.teacher_id == e_id:
                            should_block = True
                        elif e_type == "group" and req.group_id == e_id:
                            should_block = True
                        elif e_type == "subgroup" and req.subgroup_id == e_id:
                            should_block = True

                        if should_block:
                            for r_id in suitable_rooms[req.id]:
                                if (req.id, d, s, r_id) in self.x:
                                    self.model.Add(self.x[(req.id, d, s, r_id)] == 0)

                        if e_type == "room" and e_id in suitable_rooms[req.id]:
                            if (req.id, d, s, e_id) in self.x:
                                self.model.Add(self.x[(req.id, d, s, e_id)] == 0)

        # 6. Режимы Repair и Incremental
        if mode in ("repair", "incremental") and base_schedule:
            locked_set = set(locked_entries or [])
            for entry in base_schedule:
                req_id = entry.get("lesson_req_id")
                if req_id and req_id in suitable_rooms:
                    b_day = entry["day_of_week"]
                    b_slot = entry["slot_num"]
                    b_room = entry["room_id"]
                    if (req_id, b_day, b_slot, b_room) in self.x:
                        var = self.x[(req_id, b_day, b_slot, b_room)]
                        if entry.get("id") in locked_set:
                            self.model.Add(var == 1)
                        else:
                            objective_terms.append(100 * (1 - var))

        if objective_terms:
            self.model.Minimize(sum(objective_terms))

    def solve(self, time_limit_seconds: Optional[int] = None) -> TimetableSolution:
        """Запуск решения задачи CP-SAT."""
        limit = time_limit_seconds or 600
        self.solver.parameters.max_time_in_seconds = float(limit)
        self.solver.parameters.num_workers = self.num_workers
        self.solver.parameters.log_search_progress = False

        start_time = time.time()
        status_code = self.solver.Solve(self.model)
        elapsed = time.time() - start_time

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN"
        }
        status_name = status_map.get(status_code, "UNKNOWN")

        entries = []
        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for (req_id, d, s, r_id), var in self.x.items():
                if self.solver.Value(var) == 1:
                    req = next(r for r in self.lesson_reqs if r.id == req_id)
                    entries.append({
                        "lesson_req_id": req.id,
                        "group_id": req.group_id,
                        "subgroup_id": req.subgroup_id,
                        "subject_id": req.subject_id,
                        "teacher_id": req.teacher_id,
                        "room_id": r_id,
                        "day_of_week": d,
                        "slot_num": s,
                        "lesson_type": req.lesson_type,
                        "week_type": req.week_type
                    })

        entries.sort(key=lambda e: (e["group_id"], e["day_of_week"], e["slot_num"], e["subgroup_id"] or 0))

        return TimetableSolution(
            status=status_name,
            objective_value=self.solver.ObjectiveValue() if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE) else -1,
            wall_time_seconds=elapsed,
            entries=entries,
            stats={
                "branches": self.solver.NumBranches(),
                "conflicts": self.solver.NumConflicts(),
                "total_lessons_scheduled": len(entries)
            }
        )
