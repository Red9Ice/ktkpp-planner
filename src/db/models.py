from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, UniqueConstraint,
    CheckConstraint, DateTime, Date, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Group(Base):
    """Учебная группа (например, 25-ИС)."""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # Код группы (например, '25-ИС')
    name = Column(String(255), nullable=False)                         # Полное название
    course = Column(Integer, nullable=False, default=1)                 # Номер курса (1..4)
    size = Column(Integer, nullable=False, default=25)                  # Общее количество студентов
    subgroups_count = Column(Integer, nullable=False, default=2)        # Число подгрупп (обычно 2)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Связи
    subgroups = relationship("Subgroup", back_populates="group", cascade="all, delete-orphan")
    workload = relationship("CurriculumWorkload", back_populates="group", cascade="all, delete-orphan")
    schedule_entries = relationship("ScheduleEntry", back_populates="group", cascade="all, delete-orphan")


class Subgroup(Base):
    """Подгруппа (ПГ.1, ПГ.2) для занятий в лабораториях и компьютерных классах."""
    __tablename__ = "subgroups"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    subgroup_num = Column(Integer, nullable=False)  # Номер подгруппы (1 или 2)
    name = Column(String(100), nullable=False)      # Название (например, '25-ИС (ПГ.1)')
    size = Column(Integer, nullable=False, default=13)  # Количество студентов в подгруппе

    __table_args__ = (
        UniqueConstraint("group_id", "subgroup_num", name="uq_group_subgroup"),
    )

    # Связи
    group = relationship("Group", back_populates="subgroups")
    schedule_entries = relationship("ScheduleEntry", back_populates="subgroup")


class Teacher(Base):
    """Преподаватель колледжа."""
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)         # Полное ФИО
    short_name = Column(String(100), nullable=False, index=True)  # Краткое имя (например, 'Иванов И.И.')
    email = Column(String(255), nullable=True)              # Электронная почта
    max_hours_per_day = Column(Integer, default=6)          # Максимум пар в день
    is_active = Column(Boolean, default=True)               # Активен ли сотрудник
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Связи
    competencies = relationship("TeacherCompetency", back_populates="teacher", cascade="all, delete-orphan")
    workload = relationship("CurriculumWorkload", back_populates="teacher")
    schedule_entries = relationship("ScheduleEntry", back_populates="teacher")


class Room(Base):
    """Аудитория или лаборатория."""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False, index=True)  # Номер или название кабинета
    room_type = Column(String(50), nullable=False)  # Тип кабинета: 'lecture', 'computer', 'lab', 'classroom', 'gym'
    capacity = Column(Integer, nullable=False, default=30)  # Вместимость (человек)
    is_active = Column(Boolean, default=True)

    # Связи
    schedule_entries = relationship("ScheduleEntry", back_populates="room")


class Subject(Base):
    """Учебная дисциплина / предмет."""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=True)   # Код предмета
    name = Column(String(255), nullable=False)             # Полное название
    short_name = Column(String(100), nullable=False)        # Сокращенное название
    required_room_type = Column(String(50), default="any")  # Требуемый тип кабинета

    # Связи
    competencies = relationship("TeacherCompetency", back_populates="subject", cascade="all, delete-orphan")
    workload = relationship("CurriculumWorkload", back_populates="subject")
    schedule_entries = relationship("ScheduleEntry", back_populates="subject")


class TeacherCompetency(Base):
    """Компетенции преподавателя (какие предметы он может вести)."""
    __tablename__ = "teacher_competencies"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("teacher_id", "subject_id", name="uq_teacher_subject"),
    )

    # Связи
    teacher = relationship("Teacher", back_populates="competencies")
    subject = relationship("Subject", back_populates="competencies")


class CurriculumWorkload(Base):
    """Учебный план / Нагрузка: Группа - Предмет - Преподаватель - Часы в неделю."""
    __tablename__ = "curriculum_workload"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    lesson_type = Column(String(20), nullable=False)  # 'whole_group' (лекция) или 'split' (лабораторная)
    week_type = Column(String(10), default="all", nullable=False)  # 'all' (каждую неделю), '1' (1-я неделя), '2' (2-я неделя)
    pairs_per_week = Column(Integer, nullable=False)   # Количество пар (90 мин) в неделю
    preferred_room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("lesson_type IN ('whole_group', 'split')", name="check_lesson_type"),
        CheckConstraint("week_type IN ('all', '1', '2')", name="check_wl_week_type"),
    )

    # Связи
    group = relationship("Group", back_populates="workload")
    subject = relationship("Subject", back_populates="workload")
    teacher = relationship("Teacher", back_populates="workload")
    preferred_room = relationship("Room")


class AvailabilityConstraint(Base):
    """Ограничения доступности: больничные, методические дни, ремонт кабинетов."""
    __tablename__ = "availability_constraints"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'teacher', 'room', 'group', 'subgroup'
    entity_id = Column(Integer, nullable=False)      # ID соответствующей сущности
    day_of_week = Column(Integer, nullable=True)     # 0=Понедельник .. 5=Суббота (NULL, если на весь период)
    slot_num = Column(Integer, nullable=True)        # Номер пары 1..6 (NULL, если весь день)
    specific_date = Column(Date, nullable=True)      # Конкретная календарная дата (для разовых отгулов/замен)
    reason = Column(String(255), nullable=True)      # Причина (например, 'Больничный', 'Ремонт')
    is_blocked = Column(Boolean, default=True)       # Заблокирован ли слот


class ScheduleEntry(Base):
    """Сгенерированная запись расписания."""
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(String(50), nullable=False, default="base", index=True)  # Идентификатор версии расписания
    day_of_week = Column(Integer, nullable=False)     # 0=Понедельник .. 4=Пятница
    slot_num = Column(Integer, nullable=False)        # Номер пары: 1..6
    week_type = Column(String(10), default="all", nullable=False)  # 'all' (обе недели), '1' (1-я неделя), '2' (2-я неделя)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    subgroup_id = Column(Integer, ForeignKey("subgroups.id", ondelete="CASCADE"), nullable=True)  # NULL для whole_group
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False)
    is_substitution = Column(Boolean, default=False)  # Является ли запись оперативной заменой
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("slot_num BETWEEN 1 AND 6", name="check_slot_num"),
        CheckConstraint("day_of_week BETWEEN 0 AND 5", name="check_day_of_week"),
        CheckConstraint("week_type IN ('all', '1', '2')", name="check_entry_week_type"),
    )

    # Связи
    group = relationship("Group", back_populates="schedule_entries")
    subgroup = relationship("Subgroup", back_populates="schedule_entries")
    subject = relationship("Subject", back_populates="schedule_entries")
    teacher = relationship("Teacher", back_populates="schedule_entries")
    room = relationship("Room", back_populates="schedule_entries")


class Substitution(Base):
    """Журнал оперативных замен преподавателей и кабинетов."""
    __tablename__ = "substitutions"

    id = Column(Integer, primary_key=True, index=True)
    schedule_entry_id = Column(Integer, ForeignKey("schedule_entries.id", ondelete="CASCADE"))
    replacement_date = Column(Date, nullable=False)                     # Дата замены
    original_teacher_id = Column(Integer, ForeignKey("teachers.id"))     # Исходный преподаватель
    replacement_teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)  # Преподаватель на замену
    replacement_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)        # Новый кабинет (при необходимости)
    status = Column(String(50), default="pending")  # Статус: 'pending' (на рассмотрении), 'approved' (утверждено), 'cancelled' (отменено)
    comment = Column(Text, nullable=True)           # Примечание диспетчера
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
