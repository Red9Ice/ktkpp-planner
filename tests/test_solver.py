import pytest
from src.solver.model import CollegeTimetableSolver, TimetableDataset
from src.solver.contiguity import add_subgroup_contiguity_and_start_constraints
from ortools.sat.python import cp_model


def test_contiguity_automaton_valid_patterns():
    """Проверка того, что непрерывные шаблоны расписания подгруппы успешно принимаются автоматом."""
    valid_patterns = [
        [0, 0, 0, 0, 0, 0],  # Выходной день
        [1, 1, 1, 0, 0, 0],  # Пары 1, 2, 3
        [0, 1, 1, 1, 0, 0],  # Пары 2, 3, 4
        [0, 0, 1, 1, 1, 1],  # Пары 3, 4, 5, 6
        [1, 1, 0, 0, 0, 0],  # Пары 1, 2
    ]

    for pat in valid_patterns:
        model = cp_model.CpModel()
        vars = [model.NewBoolVar(f"x_{i}") for i in range(6)]
        for i, val in enumerate(pat):
            model.Add(vars[i] == val)
        add_subgroup_contiguity_and_start_constraints(model, vars, max_start_slot=3)
        solver = cp_model.CpSolver()
        res = solver.Solve(model)
        assert res in (cp_model.OPTIMAL, cp_model.FEASIBLE), f"Шаблон {pat} должен быть допустимым"


def test_contiguity_automaton_invalid_gap():
    """Проверка того, что шаблоны с окнами внутри дня или с поздним стартом отклоняются решателем."""
    invalid_patterns = [
        [1, 0, 1, 0, 0, 0],  # «Окно» на 2-й паре!
        [0, 1, 0, 1, 0, 0],  # «Окно» на 3-й паре!
        [1, 1, 0, 1, 1, 0],  # «Окно» на 3-й паре!
        [0, 0, 0, 1, 1, 0],  # Старт с 4-й пары (нарушение ограничения start <= 3)!
    ]

    for pat in invalid_patterns:
        model = cp_model.CpModel()
        vars = [model.NewBoolVar(f"x_{i}") for i in range(6)]
        for i, val in enumerate(pat):
            model.Add(vars[i] == val)
        add_subgroup_contiguity_and_start_constraints(model, vars, max_start_slot=3)
        solver = cp_model.CpSolver()
        res = solver.Solve(model)
        assert res in (cp_model.INFEASIBLE, cp_model.MODEL_INVALID), f"Шаблон {pat} должен быть недопустимым"


def test_solver_sample_dataset():
    """Тестирование полного цикла работы решателя на тестовом наборе данных КТКПП."""
    dataset = TimetableDataset(
        groups=[{"id": 1, "code": "ИС-11", "name": "Информационные системы", "course": 1, "size": 25}],
        subgroups=[
            {"id": 1, "group_id": 1, "subgroup_num": 1, "name": "ИС-11 (ПГ.1)", "size": 13},
            {"id": 2, "group_id": 1, "subgroup_num": 2, "name": "ИС-11 (ПГ.2)", "size": 12}
        ],
        teachers=[
            {"id": 1, "full_name": "Иванов И.И.", "short_name": "Иванов И.И.", "is_active": True},
            {"id": 2, "full_name": "Петров П.П.", "short_name": "Петров П.П.", "is_active": True}
        ],
        rooms=[
            {"id": 1, "number": "205", "room_type": "classroom", "capacity": 30, "is_active": True},
            {"id": 2, "number": "403", "room_type": "computer", "capacity": 15, "is_active": True}
        ],
        subjects=[
            {"id": 1, "code": "МАТ", "name": "Математика", "short_name": "Математика", "required_room_type": "classroom"},
            {"id": 2, "code": "ИНФ", "name": "Информатика", "short_name": "Информатика", "required_room_type": "computer"},
            {"id": 3, "code": "ПРЕДПР", "name": "Основы предпринимательства", "short_name": "Предпринимательство", "required_room_type": "classroom"}
        ],
        curriculum_workload=[
            {"id": 1, "group_id": 1, "subject_id": 1, "teacher_id": 1, "lesson_type": "whole_group", "week_type": "all", "pairs_per_week": 2},
            {"id": 2, "group_id": 1, "subject_id": 2, "teacher_id": 2, "lesson_type": "split", "week_type": "all", "pairs_per_week": 2},
            # Чередование: 1-я неделя Предпринимательство, 2-я неделя Математика
            {"id": 3, "group_id": 1, "subject_id": 3, "teacher_id": 1, "lesson_type": "whole_group", "week_type": "1", "pairs_per_week": 1},
            {"id": 4, "group_id": 1, "subject_id": 1, "teacher_id": 2, "lesson_type": "whole_group", "week_type": "2", "pairs_per_week": 1}
        ]
    )

    solver = CollegeTimetableSolver(dataset, days_per_week=5, slots_per_day=6)
    solver.build_model(mode="full")
    solution = solver.solve(time_limit_seconds=10)

    assert solution.status in ("OPTIMAL", "FEASIBLE")
    # 2 whole-group (all) + 4 split (all) + 1 week1 + 1 week2 = 8 записей
    assert len(solution.entries) == 8
