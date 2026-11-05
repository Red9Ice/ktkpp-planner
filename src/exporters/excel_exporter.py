import io
from typing import List, Dict, Any, Optional, Tuple
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from src.config.settings import settings

ALL_DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]


class ExcelTimetableExporter:
    """
    Экспортирует сгенерированное расписание в сводную таблицу Excel (.xlsx)
    с объединенными ячейками для общих лекций (whole-group) и раздельными колонками подгрупп (ПГ.1 и ПГ.2).
    """

    def __init__(self, dataset_dict: Dict[str, Any], days_count: int = settings.DAYS_PER_WEEK):
        self.days_count = days_count
        self.day_names = ALL_DAY_NAMES[:self.days_count]
        self.groups = {g["id"]: g for g in dataset_dict.get("groups", [])}
        self.teachers = {t["id"]: t for t in dataset_dict.get("teachers", [])}
        self.rooms = {r["id"]: r for r in dataset_dict.get("rooms", [])}
        self.subjects = {s["id"]: s for s in dataset_dict.get("subjects", [])}
        self.subgroups = {sg["id"]: sg for sg in dataset_dict.get("subgroups", [])}

        self.group_subgroups = {}
        for sg in dataset_dict.get("subgroups", []):
            self.group_subgroups.setdefault(sg["group_id"], []).append(sg)

    def export(self, schedule_entries: List[Dict[str, Any]], output_path: Optional[str] = None) -> io.BytesIO:
        """Создает книгу Excel, форматирует шапку, сетку и заполняет уроками."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Расписание КТКПП"

        # Стили оформления таблицы
        thin_border = Border(
            left=Side(style='thin', color='A0A0A0'),
            right=Side(style='thin', color='A0A0A0'),
            top=Side(style='thin', color='A0A0A0'),
            bottom=Side(style='thin', color='A0A0A0')
        )
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        sub_header_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
        sub_header_font = Font(name="Calibri", size=10, bold=True, color="000000")
        day_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        day_font = Font(name="Calibri", size=11, bold=True, color="1F497D")
        cell_font = Font(name="Calibri", size=9)
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # 1. Построение шапки таблицы
        ws.cell(row=1, column=1, value="День").font = header_font
        ws.cell(row=1, column=1).fill = header_fill
        ws.cell(row=1, column=1).alignment = center_align

        ws.cell(row=1, column=2, value="Пара").font = header_font
        ws.cell(row=1, column=2).fill = header_fill
        ws.cell(row=1, column=2).alignment = center_align

        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)
        ws.merge_cells(start_row=1, start_column=2, end_row=2, end_column=2)

        sorted_groups = sorted(self.groups.values(), key=lambda g: g["code"])
        group_col_map: Dict[int, Tuple[int, int]] = {}  # group_id -> (col_pg1, col_pg2)

        col = 3
        for grp in sorted_groups:
            col_start = col
            col_end = col + 1
            group_col_map[grp["id"]] = (col_start, col_end)

            ws.cell(row=1, column=col_start, value=grp["code"]).font = header_font
            ws.cell(row=1, column=col_start).fill = header_fill
            ws.cell(row=1, column=col_start).alignment = center_align
            ws.merge_cells(start_row=1, start_column=col_start, end_row=1, end_column=col_end)

            ws.cell(row=2, column=col_start, value="ПГ.1").font = sub_header_font
            ws.cell(row=2, column=col_start).fill = sub_header_fill
            ws.cell(row=2, column=col_start).alignment = center_align

            ws.cell(row=2, column=col_end, value="ПГ.2").font = sub_header_font
            ws.cell(row=2, column=col_end).fill = sub_header_fill
            ws.cell(row=2, column=col_end).alignment = center_align

            col += 2

        # 2. Построение строк: self.days_count дней недели * 6 пар
        current_row = 3
        slot_row_map: Dict[Tuple[int, int], int] = {}  # (day, slot) -> row_num

        for day_idx in range(self.days_count):
            day_start_row = current_row
            for slot_num in range(1, 7):
                slot_row_map[(day_idx, slot_num)] = current_row

                ws.cell(row=current_row, column=2, value=slot_num).alignment = center_align
                ws.cell(row=current_row, column=2).font = Font(bold=True)
                ws.cell(row=current_row, column=2).border = thin_border

                for c in range(3, col):
                    cell = ws.cell(row=current_row, column=c)
                    cell.border = thin_border
                    cell.alignment = center_align

                current_row += 1

            # Объединение ячейки дня недели
            ws.cell(row=day_start_row, column=1, value=self.day_names[day_idx]).font = day_font
            ws.cell(row=day_start_row, column=1).fill = day_fill
            ws.cell(row=day_start_row, column=1).alignment = center_align
            ws.merge_cells(start_row=day_start_row, start_column=1, end_row=current_row - 1, end_column=1)

        # 3. Заполнение сетки уроками
        grid: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
        for e in schedule_entries:
            key = (e["group_id"], e["day_of_week"], e["slot_num"])
            grid.setdefault(key, []).append(e)

        for (grp_id, day_idx, slot_num), entries in grid.items():
            if grp_id not in group_col_map or (day_idx, slot_num) not in slot_row_map:
                continue

            row_num = slot_row_map[(day_idx, slot_num)]
            col_pg1, col_pg2 = group_col_map[grp_id]

            whole_entries = [e for e in entries if e["lesson_type"] == "whole_group"]
            if whole_entries:
                text_lines = []
                # Сортируем: сначала 1-я неделя (или all), затем 2-я неделя
                sorted_entries = sorted(whole_entries, key=lambda x: (0 if x.get("week_type") == "1" else (1 if x.get("week_type") == "all" else 2)))
                for e in sorted_entries:
                    subj = self.subjects.get(e["subject_id"], {}).get("short_name", "")
                    teach = self.teachers.get(e["teacher_id"], {}).get("short_name", "")
                    rm = self.rooms.get(e["room_id"], {}).get("number", "")
                    w_type = e.get("week_type", "all")

                    prefix = ""
                    if w_type == "1":
                        prefix = "[1 нед] "
                    elif w_type == "2":
                        prefix = "[2 нед] "

                    text_lines.append(f"{prefix}{subj} ({rm})")

                cell = ws.cell(row=row_num, column=col_pg1, value="\n".join(text_lines))
                cell.font = cell_font
                cell.alignment = center_align
                ws.merge_cells(start_row=row_num, start_column=col_pg1, end_row=row_num, end_column=col_pg2)
            else:
                for e in entries:
                    sg_id = e.get("subgroup_id")
                    sg_obj = self.subgroups.get(sg_id)
                    sg_num = sg_obj.get("subgroup_num", 1) if sg_obj else 1
                    target_col = col_pg1 if sg_num == 1 else col_pg2

                    subj = self.subjects.get(e["subject_id"], {}).get("short_name", "")
                    teach = self.teachers.get(e["teacher_id"], {}).get("short_name", "")
                    rm = self.rooms.get(e["room_id"], {}).get("number", "")
                    w_type = e.get("week_type", "all")

                    prefix = ""
                    if w_type == "1":
                        prefix = "[1 нед] "
                    elif w_type == "2":
                        prefix = "[2 нед] "

                    current_val = ws.cell(row=row_num, column=target_col).value
                    new_val = f"{prefix}{subj} ({rm})"
                    cell_text = f"{current_val}\n{new_val}" if current_val else new_val

                    cell = ws.cell(row=row_num, column=target_col, value=cell_text)
                    cell.font = cell_font
                    cell.alignment = center_align

        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 8
        for c in range(3, col):
            col_letter = get_column_letter(c)
            ws.column_dimensions[col_letter].width = 22

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        if output_path:
            with open(output_path, "wb") as f:
                f.write(output.getbuffer())

        return output
