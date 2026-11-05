-- 001_initial_schema.sql
-- Схема базы данных PostgreSQL для системы расписания колледжа и облачных ботов

CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,       -- Код группы (например, '25-ИС')
    name VARCHAR(255) NOT NULL,             -- Полное наименование группы
    course INTEGER NOT NULL DEFAULT 1,      -- Номер курса
    size INTEGER NOT NULL DEFAULT 25,       -- Общее количество студентов
    subgroups_count INTEGER NOT NULL DEFAULT 2, -- Количество подгрупп
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subgroups (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    subgroup_num INTEGER NOT NULL,          -- Номер подгруппы (1 или 2)
    name VARCHAR(100) NOT NULL,             -- Название (например, '25-ИС (ПГ.1)')
    size INTEGER NOT NULL DEFAULT 13,       -- Количество студентов в подгруппе
    UNIQUE (group_id, subgroup_num)
);

CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,        -- Полное ФИО преподавателя
    short_name VARCHAR(100) NOT NULL,        -- Краткое имя (например, 'Иванов И.И.')
    email VARCHAR(255),                     -- Электронная почта
    max_hours_per_day INTEGER DEFAULT 6,    -- Максимальное число пар в день
    is_active BOOLEAN DEFAULT TRUE,         -- Активен ли сотрудник
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) UNIQUE NOT NULL,     -- Номер или название кабинета (например, '301', 'Лаб-2')
    room_type VARCHAR(50) NOT NULL,         -- Тип: 'lecture', 'computer', 'lab', 'gym'
    capacity INTEGER NOT NULL DEFAULT 30,   -- Вместимость (человек)
    is_active BOOLEAN DEFAULT TRUE          -- Доступен ли кабинет
);

CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE,                -- Код предмета
    name VARCHAR(255) NOT NULL,             -- Полное название дисциплины
    short_name VARCHAR(100) NOT NULL,       -- Краткое наименование
    required_room_type VARCHAR(50) DEFAULT 'any' -- Требуемый тип кабинета ('lecture', 'computer', 'lab', 'any')
);

CREATE TABLE IF NOT EXISTS teacher_competencies (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    UNIQUE (teacher_id, subject_id)
);

CREATE TABLE IF NOT EXISTS curriculum_workload (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT,
    lesson_type VARCHAR(20) NOT NULL,       -- 'whole_group' (вся группа) или 'split' (по подгруппам)
    week_type VARCHAR(10) NOT NULL DEFAULT 'all', -- 'all' (каждую неделю), '1' (1-я неделя), '2' (2-я неделя)
    pairs_per_week INTEGER NOT NULL,        -- Количество академических пар (90 мин) в неделю
    preferred_room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    CONSTRAINT check_lesson_type CHECK (lesson_type IN ('whole_group', 'split')),
    CONSTRAINT check_wl_week_type CHECK (week_type IN ('all', '1', '2'))
);

CREATE TABLE IF NOT EXISTS availability_constraints (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,       -- Тип сущности: 'teacher', 'room', 'group', 'subgroup'
    entity_id INTEGER NOT NULL,             -- ID сущности
    day_of_week INTEGER,                    -- День недели: 0=Понедельник .. 5=Суббота (NULL, если на все дни)
    slot_num INTEGER,                       -- Номер пары: 1..6 (NULL, если на весь день)
    specific_date DATE,                     -- Конкретная дата (для разовых отгулов/ремонтов)
    reason VARCHAR(255),                    -- Причина блокировки
    is_blocked BOOLEAN DEFAULT TRUE         -- Заблокирован ли слот
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id SERIAL PRIMARY KEY,
    version_id VARCHAR(50) NOT NULL DEFAULT 'base', -- Идентификатор версии расписания
    day_of_week INTEGER NOT NULL,           -- День недели: 0=Понедельник .. 4=Пятница
    slot_num INTEGER NOT NULL,              -- Номер пары: 1..6
    week_type VARCHAR(10) NOT NULL DEFAULT 'all',   -- 'all' (обе недели), '1' (1-я неделя), '2' (2-я неделя)
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    subgroup_id INTEGER REFERENCES subgroups(id) ON DELETE CASCADE, -- NULL для whole_group
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    is_substitution BOOLEAN DEFAULT FALSE,  -- Флаг оперативной замены
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_slot_num CHECK (slot_num BETWEEN 1 AND 6),
    CONSTRAINT check_day_of_week CHECK (day_of_week BETWEEN 0 AND 5),
    CONSTRAINT check_entry_week_type CHECK (week_type IN ('all', '1', '2'))
);

-- Индексы для ускорения выборок расписания
CREATE INDEX IF NOT EXISTS idx_sched_group_day_slot ON schedule_entries (group_id, day_of_week, slot_num);
CREATE INDEX IF NOT EXISTS idx_sched_teacher_day_slot ON schedule_entries (teacher_id, day_of_week, slot_num);
CREATE INDEX IF NOT EXISTS idx_sched_room_day_slot ON schedule_entries (room_id, day_of_week, slot_num);
CREATE INDEX IF NOT EXISTS idx_sched_version ON schedule_entries (version_id);

CREATE TABLE IF NOT EXISTS substitutions (
    id SERIAL PRIMARY KEY,
    schedule_entry_id INTEGER REFERENCES schedule_entries(id) ON DELETE CASCADE,
    replacement_date DATE NOT NULL,         -- Дата проведения замены
    original_teacher_id INTEGER REFERENCES teachers(id),
    replacement_teacher_id INTEGER REFERENCES teachers(id),
    replacement_room_id INTEGER REFERENCES rooms(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- Статус: 'pending', 'approved', 'cancelled'
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
