import json
import os

GROUPS_DEF = [
    # 1 курс (16 групп)
    ("С-11", "Строительство и эксплуатация зданий и сооружений", 1),
    ("ОС-11", "Отделочные строительные работы", 1),
    ("ИС-11", "Информационные системы и программирование", 1),
    ("ИС-12", "Информационные системы и программирование", 1),
    ("АП-11", "Автоматизация технологических процессов и производств", 1),
    ("АП-12", "Автоматизация технологических процессов и производств", 1),
    ("ТХ-11", "Технология хлеба, кондитерских и макаронных изделий", 1),
    ("З-12", "Земельно-имущественные отношения", 1),
    ("Т-11", "Технология продукции общественного питания", 1),
    ("ТД-11", "Товароведение и экспертиза качества потребительских товаров", 1),
    ("ТК-11", "Коммерция (по отраслям)", 1),
    ("ТК-12", "Коммерция (по отраслям)", 1),
    ("ГД-12", "Гостиничное дело", 1),
    ("ПД-11", "Поварское и кондитерское дело", 1),
    ("ПД-12", "Поварское и кондитерское дело", 1),
    ("ТМ-11", "Технология мяса и мясных продуктов", 1),

    # 2 курс (15 групп)
    ("ТК-21", "Коммерция (по отраслям)", 2),
    ("ТК-22", "Коммерция (по отраслям)", 2),
    ("ПД-21", "Поварское и кондитерское дело", 2),
    ("ПД-22", "Поварское и кондитерское дело", 2),
    ("ПД-23", "Поварское и кондитерское дело", 2),
    ("С-21", "Строительство и эксплуатация зданий и сооружений", 2),
    ("ОС-21", "Отделочные строительные работы", 2),
    ("ИС-21", "Информационные системы и программирование", 2),
    ("ИС-22", "Информационные системы и программирование", 2),
    ("ГД-22", "Гостиничное дело", 2),
    ("АП-21", "Автоматизация технологических процессов и производств", 2),
    ("Т-21", "Технология продукции общественного питания", 2),
    ("ТД-21", "Товароведение и торговое дело", 2),
    ("ТХ-21", "Технология хлеба, кондитерских и макаронных изделий", 2),
    ("З-22", "Земельно-имущественные отношения", 2),

    # 3 курс (7 групп)
    ("ПД-31", "Поварское и кондитерское дело", 3),
    ("ПД-32", "Поварское и кондитерское дело", 3),
    ("ТК-31", "Коммерция (по отраслям)", 3),
    ("Т-31", "Технология продукции общественного питания", 3),
    ("ТД-31", "Товароведение и торговое дело", 3),
    ("З-32", "Земельно-имущественные отношения", 3),
    ("ТХ-31", "Технология хлеба, кондитерских и макаронных изделий", 3),

    # 4 курс (7 групп)
    ("ПД-41", "Поварское и кондитерское дело", 4),
    ("ПД-42", "Поварское и кондитерское дело", 4),
    ("ТК-41", "Коммерция (по отраслям)", 4),
    ("Т-41", "Технология продукции общественного питания", 4),
    ("ТХ-41", "Технология хлеба, кондитерских и макаронных изделий", 4),
    ("З-41", "Земельно-имущественные отношения", 4),
    ("З-42", "Земельно-имущественные отношения", 4),
]

ROOMS_DEF = [
    # Аудитории общего профиля
    ("1", "classroom", 30), ("4", "classroom", 30), ("5", "classroom", 30),
    ("30", "classroom", 30), ("31", "classroom", 30), ("33", "classroom", 30),
    ("35", "classroom", 30), ("36", "classroom", 30), ("40", "classroom", 30),
    ("41", "classroom", 30), ("43", "classroom", 30), ("45", "classroom", 30),
    ("46", "classroom", 30), ("48", "classroom", 30), ("50", "classroom", 30),
    ("51", "classroom", 30), ("52", "classroom", 30), ("202", "classroom", 30),
    ("204", "classroom", 30), ("205", "classroom", 30), ("207", "classroom", 30),
    ("209", "classroom", 30), ("212", "classroom", 30), ("301", "classroom", 30),
    ("302", "classroom", 30), ("306", "classroom", 30), ("307", "classroom", 30),
    ("401", "classroom", 30), ("402", "classroom", 30), ("405", "classroom", 30),
    ("406", "classroom", 30), ("407", "classroom", 30),

    # Лаборатории, компьютерные классы и спецкабинеты
    ("105в", "chemistry_lab", 30),
    ("201", "computer", 18),
    ("201в", "computer", 18),
    ("203", "lab", 20),
    ("203б", "computer", 18),
    ("203в", "obzr_lab", 30),
    ("205б", "lab", 25),
    ("206", "language", 18),
    ("206б", "computer", 18),
    ("208", "language", 18),
    ("403", "computer", 18),
    ("404", "computer", 18),
    ("Мастерская 103б", "workshop", 25),

    # Специальные помещения
    ("С/з", "gym", 80),
    ("Библ", "library", 40),
    ("К/з", "hall", 60),
    ("Акт.зал", "hall", 120)
]

def generate_ktkpp_dataset():
    groups = []
    subgroups = []
    sg_id = 1
    for idx, (code, name, course) in enumerate(GROUPS_DEF, start=1):
        groups.append({
            "id": idx,
            "code": code,
            "name": name,
            "course": course,
            "size": 25,
            "subgroups_count": 2
        })
        subgroups.append({
            "id": sg_id,
            "group_id": idx,
            "subgroup_num": 1,
            "name": f"{code} (ПГ.1)",
            "size": 13
        })
        sg_id += 1
        subgroups.append({
            "id": sg_id,
            "group_id": idx,
            "subgroup_num": 2,
            "name": f"{code} (ПГ.2)",
            "size": 12
        })
        sg_id += 1

    rooms = []
    for idx, (num, r_type, cap) in enumerate(ROOMS_DEF, start=1):
        rooms.append({
            "id": idx,
            "number": num,
            "room_type": r_type,
            "capacity": cap,
            "is_active": True
        })

    # Справочник предметов, встречающихся в расписании КТКПП
    subjects_data = [
        ("РАЗГ", "Разговоры о важном", "Разговоры о важном", "classroom"),
        ("КЛЧАС", "Классный час", "Классный час", "classroom"),
        ("МАТ", "Математика", "Математика", "classroom"),
        ("РУС", "Русский язык", "Русский язык", "classroom"),
        ("ЛИТ", "Литература", "Литература", "classroom"),
        ("ИСТ", "История России", "История", "classroom"),
        ("ОБЩ", "Обществознание", "Обществознание", "classroom"),
        ("ФИЗ", "Физика", "Физика", "classroom"),
        ("ХИМ", "Химия", "Химия", "chemistry_lab"),
        ("БИО", "Биология", "Биология", "classroom"),
        ("ГЕО", "География", "География", "classroom"),
        ("ИНФ", "Информатика", "Информатика", "computer"),
        ("ИНЯЗ", "Иностранный язык", "Иностранный язык", "language"),
        ("ОБИЗР", "Основы безопасности и защиты Родины", "ОБиЗР", "obzr_lab"),
        ("БЖД", "Безопасность жизнедеятельности", "БЖД", "obzr_lab"),
        ("ФК", "Физическая культура", "ФК", "gym"),
        ("МДК0101", "МДК 01.01", "МДК 01.01", "lab"),
        ("МДК0102", "МДК 01.02", "МДК 01.02", "lab"),
        ("МДК0201", "МДК 02.01", "МДК 02.01", "lab"),
        ("МДК0202", "МДК 02.02", "МДК 02.02", "lab"),
        ("МДК0301", "МДК 03.01", "МДК 03.01", "lab"),
        ("ТЕХМЕХ", "Техническая механика", "Техническая механика", "classroom"),
        ("МИКРОБ", "Микробиология", "Микробиология", "lab"),
        ("ЭЛТЕХ", "Электротехника", "Электротехника", "lab"),
        ("ИТПД", "Информационные технологии в проф. деятельности", "ИТПД", "computer"),
        ("ПОПД", "Правовые основы проф. деятельности", "ПОПД", "classroom"),
        ("КУРС", "Курсовой проект", "Курсовой проект", "lab"),
        ("ПРАКТ", "Учебная практика", "Учебная практика", "workshop")
    ]

    subjects = []
    for idx, (code, name, short_name, r_type) in enumerate(subjects_data, start=1):
        subjects.append({
            "id": idx,
            "code": code,
            "name": name,
            "short_name": short_name,
            "required_room_type": r_type
        })

    # Список преподавателей колледжа (на основе предметных кафедр)
    teachers_data = [
        "Иванов И.И.", "Петрова А.С.", "Смирнов А.В.", "Кузнецова Е.П.", "Соколов Д.Н.",
        "Морозова О.И.", "Васильев С.М.", "Попова Н.Ю.", "Новиков К.Д.", "Федорова М.А.",
        "Брызгалов Д.А.", "Жукова Е.П.", "Печенкина С.С.", "Лебедев А.Н.", "Козлова Т.В.",
        "Семенов В.П.", "Егорова И.С.", "Павлов Г.М.", "Ковалева Д.А.", "Григорьев А.С."
    ]
    teachers = []
    for idx, name in enumerate(teachers_data, start=1):
        teachers.append({
            "id": idx,
            "full_name": name,
            "short_name": name,
            "email": f"teacher{idx}@ktkpp.ru",
            "max_hours_per_day": 6,
            "is_active": True
        })

    # Формирование типовой учебной нагрузки для 45 групп
    workload = []
    wl_id = 1
    for g in groups:
        g_id = g["id"]
        course = g["course"]

        # 1. Понедельник: Разговоры о важном (для 1 курса) или Классный час (для 2-4 курсов)
        subj_fixed_id = 1 if course == 1 else 2
        workload.append({
            "id": wl_id,
            "group_id": g_id,
            "subject_id": subj_fixed_id,
            "teacher_id": (g_id % len(teachers)) + 1,
            "lesson_type": "whole_group",
            "pairs_per_week": 1
        })
        wl_id += 1

        # 2. Физкультура (2 пары в неделю)
        workload.append({
            "id": wl_id,
            "group_id": g_id,
            "subject_id": 16, # ФК
            "teacher_id": 7,  # Васильев С.М.
            "lesson_type": "whole_group",
            "pairs_per_week": 2,
            "preferred_room_id": next(r["id"] for r in rooms if r["number"] == "С/з")
        })
        wl_id += 1

        # 3. Общеобразовательные или профильные предметы
        if course == 1:
            # Математика
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 3, "teacher_id": 2, "lesson_type": "whole_group", "pairs_per_week": 3})
            wl_id += 1
            # Информатика (split)
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 12, "teacher_id": 1, "lesson_type": "split", "pairs_per_week": 2})
            wl_id += 1
            # Иностранный язык (split)
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 13, "teacher_id": 5, "lesson_type": "split", "pairs_per_week": 2})
            wl_id += 1
            # История
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 6, "teacher_id": 6, "lesson_type": "whole_group", "pairs_per_week": 2})
            wl_id += 1
            # ОБиЗР
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 14, "teacher_id": 9, "lesson_type": "whole_group", "pairs_per_week": 2})
            wl_id += 1
        else:
            # Спецдисциплины для 2-4 курсов
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 17, "teacher_id": 3, "lesson_type": "whole_group", "pairs_per_week": 3})
            wl_id += 1
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 18, "teacher_id": 4, "lesson_type": "split", "pairs_per_week": 2})
            wl_id += 1
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 25, "teacher_id": 8, "lesson_type": "split", "pairs_per_week": 2})
            wl_id += 1
            workload.append({"id": wl_id, "group_id": g_id, "subject_id": 26, "teacher_id": 10, "lesson_type": "whole_group", "pairs_per_week": 2})
            wl_id += 1

    return {
        "college": "КОГПОАУ КТКПП",
        "groups": groups,
        "subgroups": subgroups,
        "rooms": rooms,
        "subjects": subjects,
        "teachers": teachers,
        "curriculum_workload": workload,
        "availability_constraints": []
    }

if __name__ == "__main__":
    data = generate_ktkpp_dataset()
    target_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples", "ktkpp_data.json")
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"KTKPP dataset successfully created: {len(data['groups'])} groups, {len(data['rooms'])} rooms.")
