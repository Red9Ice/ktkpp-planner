from datetime import date, datetime
from typing import Tuple


def get_academic_week_info(
    target_date: date = None,
    academic_year_start: date = None
) -> Tuple[int, int, str]:
    """
    Определяет номер учебной недели и тип чередования (1-я или 2-я неделя).
    Отсчет ведется с 1 сентября текущего учебного года.

    Возвращает кортеж:
    - absolute_week_num: порядковый номер учебной недели в семестре (1..17+)
    - week_type: 1 (1-я неделя, под чертой / числитель) или 2 (2-я неделя, под линией / знаменатель)
    - week_name: строковое описание ('1-я неделя' или '2-я неделя')
    """
    if target_date is None:
        target_date = date.today()

    if academic_year_start is None:
        # Учебный год начинается 1 сентября
        year = target_date.year if target_date.month >= 8 else target_date.year - 1
        academic_year_start = date(year, 9, 1)

    # Находим понедельник недели, в которую попадает 1 сентября
    start_monday = academic_year_start - \
        datetime.timedelta(days=academic_year_start.weekday()) if hasattr(datetime, "timedelta") else academic_year_start
    import datetime as dt
    start_monday = academic_year_start - dt.timedelta(days=academic_year_start.weekday())

    # Понедельник целевой недели
    target_monday = target_date - dt.timedelta(days=target_date.weekday())

    # Разница в днях и вычисление номера недели
    delta_days = (target_monday - start_monday).days
    absolute_week_num = max(1, (delta_days // 7) + 1)

    # Нечетные недели = 1-я неделя (подчеркнутая), Четные недели = 2-я неделя (под линией)
    week_type = 1 if (absolute_week_num % 2 == 1) else 2
    week_name = f"{week_type}-я неделя ({'подчеркнутая' if week_type == 1 else 'под линией'})"

    return absolute_week_num, week_type, week_name
