import argparse
import json
import logging
import os
import sys
from typing import Dict, Any

from src.config.settings import settings
from src.db.session import SessionLocal, init_db
from src.db.models import Group, Subgroup, Teacher, Room, Subject, CurriculumWorkload, AvailabilityConstraint, ScheduleEntry
from src.solver.model import CollegeTimetableSolver, TimetableDataset
from src.exporters.excel_exporter import ExcelTimetableExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TimetableRunner")


def load_dataset_from_json(json_path: str) -> TimetableDataset:
    """Загрузка данных справочников и нагрузки из JSON-файла."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return TimetableDataset(
        groups=data["groups"],
        subgroups=data["subgroups"],
        teachers=data["teachers"],
        rooms=data["rooms"],
        subjects=data["subjects"],
        curriculum_workload=data["curriculum_workload"],
        availability_constraints=data.get("availability_constraints", [])
    )


def load_dataset_from_db() -> TimetableDataset:
    """Загрузка данных справочников и нагрузки напрямую из базы данных PostgreSQL."""
    with SessionLocal() as db:
        groups = [{"id": g.id, "code": g.code, "name": g.name, "course": g.course, "size": g.size} for g in db.query(Group).all()]
        subgroups = [{"id": sg.id, "group_id": sg.group_id, "subgroup_num": sg.subgroup_num, "name": sg.name, "size": sg.size} for sg in db.query(Subgroup).all()]
        teachers = [{"id": t.id, "full_name": t.full_name, "short_name": t.short_name, "is_active": t.is_active} for t in db.query(Teacher).all()]
        rooms = [{"id": r.id, "number": r.number, "room_type": r.room_type, "capacity": r.capacity, "is_active": r.is_active} for r in db.query(Room).all()]
        subjects = [{"id": s.id, "code": s.code, "name": s.name, "short_name": s.short_name, "required_room_type": s.required_room_type} for s in db.query(Subject).all()]
        workload = [
            {
                "id": w.id,
                "group_id": w.group_id,
                "subject_id": w.subject_id,
                "teacher_id": w.teacher_id,
                "lesson_type": w.lesson_type,
                "pairs_per_week": w.pairs_per_week,
                "preferred_room_id": w.preferred_room_id
            }
            for w in db.query(CurriculumWorkload).all()
        ]
        constraints = [
            {
                "id": c.id,
                "entity_type": c.entity_type,
                "entity_id": c.entity_id,
                "day_of_week": c.day_of_week,
                "slot_num": c.slot_num,
                "is_blocked": c.is_blocked
            }
            for c in db.query(AvailabilityConstraint).all()
        ]

    return TimetableDataset(
        groups=groups,
        subgroups=subgroups,
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        curriculum_workload=workload,
        availability_constraints=constraints
    )


def save_solution_to_db(solution_entries: list, version_id: str = "base"):
    """Сохранение найденного расписания в базу данных."""
    with SessionLocal() as db:
        # Очистка предыдущего расписания этой версии
        db.query(ScheduleEntry).filter(ScheduleEntry.version_id == version_id).delete()

        # Вставка новых сгенерированных уроков
        for e in solution_entries:
            entry = ScheduleEntry(
                version_id=version_id,
                day_of_week=e["day_of_week"],
                slot_num=e["slot_num"],
                group_id=e["group_id"],
                subgroup_id=e["subgroup_id"],
                subject_id=e["subject_id"],
                teacher_id=e["teacher_id"],
                room_id=e["room_id"],
                is_substitution=False
            )
            db.add(entry)
        db.commit()
        logger.info(f"Успешно сохранено {len(solution_entries)} уроков в БД (версия: {version_id}).")


def main():
    """Точка входа для запуска решения расписания из командной строки."""
    parser = argparse.ArgumentParser(description="Запуск генератора расписания колледжа (CP-SAT Solver)")
    parser.add_argument("--mode", choices=["full", "repair", "incremental"], default="full", help="Режим работы решателя")
    parser.add_argument("--sample", action="store_true", help="Принудительно использовать тестовый sample_data.json")
    parser.add_argument("--dataset", type=str, default=None, help="Путь к конкретному JSON-файлу с датасетом")
    parser.add_argument("--time-limit", type=int, default=settings.SOLVER_MAX_TIME_SECONDS, help="Лимит времени в секундах")
    parser.add_argument("--export-excel", type=str, default="College_Timetable.xlsx", help="Путь для сохранения Excel")
    args = parser.parse_args()

    init_db()

    # Загрузка данных
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples")
    ktkpp_path = os.path.join(samples_dir, "ktkpp_data.json")
    sample_path = os.path.join(samples_dir, "sample_data.json")

    chosen_file = args.dataset or (ktkpp_path if os.path.exists(ktkpp_path) and not args.sample else sample_path)

    if args.sample or args.dataset or not os.path.exists(ktkpp_path):
        logger.info(f"Загрузка данных из JSON-файла: {chosen_file}")
        dataset = load_dataset_from_json(chosen_file)
    else:
        logger.info("Попытка загрузки данных из базы данных...")
        dataset = load_dataset_from_db()
        if not dataset.groups:
            logger.info(f"База данных пуста, загрузка эталонного датасета КТКПП: {chosen_file}")
            dataset = load_dataset_from_json(chosen_file)

    logger.info(f"Данные загружены: {len(dataset.groups)} групп, {len(dataset.teachers)} преподавателей, {len(dataset.rooms)} аудиторий.")

    # Инициализация решателя
    solver = CollegeTimetableSolver(
        dataset=dataset,
        days_per_week=settings.DAYS_PER_WEEK,
        slots_per_day=settings.SLOTS_PER_DAY,
        max_start_slot=3,
        num_workers=settings.SOLVER_NUM_WORKERS
    )

    logger.info(f"Построение модели CP-SAT (режим={args.mode}, всего требований к парам={len(solver.lesson_reqs)})...")
    solver.build_model(mode=args.mode)

    logger.info(f"Запуск решения с ограничением времени {args.time_limit} сек...")
    solution = solver.solve(time_limit_seconds=args.time_limit)

    logger.info(f"Статус решения: {solution.status} за {solution.wall_time_seconds:.2f} сек.")
    logger.info(f"Значение целевой функции: {solution.objective_value}")
    logger.info(f"Всего назначено уроков: {len(solution.entries)}")

    if solution.status in ("OPTIMAL", "FEASIBLE"):
        # Сохранение в БД
        try:
            save_solution_to_db(solution.entries, version_id="base")
        except Exception as ex:
            logger.warning(f"Не удалось сохранить напрямую в БД: {ex}")

        # Экспорт в Excel
        dataset_dict = {
            "groups": dataset.groups,
            "subgroups": dataset.subgroups,
            "teachers": dataset.teachers,
            "rooms": dataset.rooms,
            "subjects": dataset.subjects
        }
        exporter = ExcelTimetableExporter(dataset_dict)
        exporter.export(solution.entries, output_path=args.export_excel)
        logger.info(f"Сводное расписание в Excel успешно сформировано: {args.export_excel}")
    else:
        logger.error(f"Решатель не смог найти допустимое расписание. Статус: {solution.status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
