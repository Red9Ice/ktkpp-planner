import io
from typing import List, Dict, Any, Optional, Tuple
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from src.config.settings import settings

ALL_DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]


class PDFTimetableExporter:
    """
    Генерирует готовые к печати сетки расписания в формате PDF для учебных групп КТКПП.
    Воспроизводит визуальное оформление официального расписания колледжа:
    - 1-я неделя: предмет подчеркнут (<u>...</u>)
    - 2-я неделя: предмет под чертой
    - Каждую неделю: обычный текст
    """

    def __init__(self, dataset_dict: Dict[str, Any], days_count: int = settings.DAYS_PER_WEEK):
        self.days_count = days_count
        self.day_names = ALL_DAY_NAMES[:self.days_count]
        self.groups = {g["id"]: g for g in dataset_dict.get("groups", [])}
        self.teachers = {t["id"]: t for t in dataset_dict.get("teachers", [])}
        self.rooms = {r["id"]: r for r in dataset_dict.get("rooms", [])}
        self.subjects = {s["id"]: s for s in dataset_dict.get("subjects", [])}
        self.subgroups = {sg["id"]: sg for sg in dataset_dict.get("subgroups", [])}

    def export_group_schedule(
        self,
        group_id: int,
        schedule_entries: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        elements = []
        styles = getSampleStyleSheet()

        grp_name = self.groups.get(group_id, {}).get("name", f"Группа {group_id}")
        grp_code = self.groups.get(group_id, {}).get("code", "")

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=15,
            leading=18,
            alignment=1,
            textColor=colors.HexColor("#1F497D")
        )
        sub_title_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#555555")
        )
        elements.append(Paragraph(f"КОГПОАУ КТКПП — Расписание занятий: {grp_code} ({grp_name})", title_style))
        elements.append(Paragraph("<u>Подчеркнуто</u> — 1-я неделя; обычный текст под чертой — 2-я неделя (отсчет с 1 сентября)", sub_title_style))
        elements.append(Spacer(1, 10))

        header_row = [
            "День недели",
            "Пара 1\n08:00-09:20",
            "Пара 2\n09:35-10:55",
            "Пара 3\n11:25-12:45",
            "Пара 4\n12:55-14:15",
            "Пара 5\n14:25-15:45",
            "Пара 6\n15:50-17:10"
        ]
        data = [header_row]

        cell_style = ParagraphStyle('CellStyle', fontSize=8, leading=10, alignment=1)

        grp_entries = [e for e in schedule_entries if e["group_id"] == group_id]
        grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        for e in grp_entries:
            grid.setdefault((e["day_of_week"], e["slot_num"]), []).append(e)

        for d in range(self.days_count):
            row = [self.day_names[d]]
            for s in range(1, 7):
                items = grid.get((d, s), [])
                if not items:
                    row.append("")
                else:
                    text_parts = []
                    # Сортируем: 1-я неделя сверху, 2-я неделя снизу
                    sorted_items = sorted(items, key=lambda x: (0 if x.get("week_type") == "1" else (1 if x.get("week_type") == "all" else 2)))
                    for item in sorted_items:
                        subj = self.subjects.get(item["subject_id"], {}).get("short_name", "")
                        teacher = self.teachers.get(item["teacher_id"], {}).get("short_name", "")
                        rm = self.rooms.get(item["room_id"], {}).get("number", "")
                        w_type = item.get("week_type", "all")
                        prefix = ""
                        if item["lesson_type"] == "split":
                            sg_num = self.subgroups.get(item["subgroup_id"], {}).get("subgroup_num", "")
                            prefix = f"[ПГ.{sg_num}] "

                        # 1-я неделя оформляется подчеркиванием <u>...</u>
                        if w_type == "1":
                            text_parts.append(f"<u><b>{prefix}{subj}</b> ({rm})</u>")
                        elif w_type == "2":
                            text_parts.append(f"<b>{prefix}{subj}</b> ({rm})")
                        else:
                            text_parts.append(f"<b>{prefix}{subj}</b><br/>{teacher} ({rm})")

                    row.append(Paragraph("<br/>".join(text_parts), cell_style))
            data.append(row)

        table = Table(data, colWidths=[90, 115, 115, 115, 115, 115, 115])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F497D")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#A0A0A0")),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#F2F2F2")),
            ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor("#1F497D")),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (0, -1), 9),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)

        if output_path:
            with open(output_path, "wb") as f:
                f.write(buffer.getbuffer())

        return buffer
