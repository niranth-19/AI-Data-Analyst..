"""Generate professional PDF reports with reportlab + matplotlib."""

import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Analysis, Dataset, Report, User
from app.schemas.common import to_serializable
from app.services.dataset_service import get_dataset_path, load_dataframe
from app.services.quality_service import analyze_quality
from app.services.stats_service import compute_column_statistics

settings = get_settings()

ACCENT = colors.HexColor("#2563eb")
LIGHT = colors.HexColor("#eff6ff")


def _render_chart_png(chart_spec: dict[str, Any]) -> bytes | None:
    chart_type = chart_spec.get("type")
    datasets = chart_spec.get("datasets", [])
    labels = chart_spec.get("labels", [])
    if not datasets or not datasets[0].get("data"):
        return None

    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=110)
    data = datasets[0]["data"]

    try:
        if chart_type in ("bar", "histogram"):
            ax.bar([str(l) for l in labels], [float(v) for v in data], color="#2563eb")
            ax.set_xticklabels([str(l) for l in labels], rotation=45, ha="right", fontsize=7)
        elif chart_type == "line":
            ax.plot([str(l) for l in labels], [float(v) for v in data], marker="o", color="#2563eb")
            ax.set_xticklabels([str(l) for l in labels], rotation=45, ha="right", fontsize=7)
        elif chart_type in ("pie", "doughnut"):
            ax.pie([float(v) for v in data], labels=[str(l) for l in labels], autopct="%1.1f%%")
        elif chart_type == "scatter":
            xs = [p["x"] for p in data]
            ys = [p["y"] for p in data]
            ax.scatter(xs, ys, s=18, color="#2563eb")
            ax.set_xlabel(str(labels[0]) if labels else "")
        else:
            ax.bar([str(l) for l in labels], [float(v) for v in data], color="#2563eb")
            ax.set_xticklabels([str(l) for l in labels], rotation=45, ha="right", fontsize=7)

        ax.set_title(chart_spec.get("title", ""), fontsize=10)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        plt.close(fig)
        return None


def _add_section_title(story, text: str) -> None:
    style = ParagraphStyle(
        "SectionTitle",
        parent=getSampleStyleSheet()["Heading2"],
        textColor=ACCENT,
        fontSize=13,
        spaceBefore=14,
        spaceAfter=6,
    )
    story.append(Paragraph(text, style))


def _style_table(table: Table) -> Table:
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def generate_report_pdf(db: Session, user: User, dataset: Dataset, report_name: str | None) -> Report:
    report_dir = settings.STORAGE_DIR / str(user.id) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"report_{uuid.uuid4().hex}.pdf"
    output_path = report_dir / stored_filename

    name = report_name or f"Report - {dataset.original_filename}"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=name,
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], textColor=ACCENT, alignment=TA_CENTER, fontSize=20
    )
    story.append(Paragraph("AI Data Analyst — Report", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>{name}</b><br/>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle("Subtitle", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.grey, fontSize=9),
    ))
    story.append(Spacer(1, 8))

    # Dataset summary
    _add_section_title(story, "1. Dataset Summary")
    df = load_dataframe(dataset)
    summary = [
        ["Attribute", "Value"],
        ["Dataset name", dataset.original_filename],
        ["Format", dataset.file_format.upper()],
        ["Rows", str(dataset.row_count)],
        ["Columns", str(dataset.column_count)],
        ["File size", f"{dataset.file_size_bytes / 1024:.1f} KB"],
        ["Uploaded", dataset.created_at.strftime("%Y-%m-%d %H:%M")],
    ]
    story.append(_style_table(Table(summary, colWidths=[40 * mm, 110 * mm])))

    # Columns
    _add_section_title(story, "2. Columns")
    col_data = [["Column", "Type"]] + [[c["name"], c["dtype"]] for c in dataset.columns]
    story.append(_style_table(Table(col_data, colWidths=[90 * mm, 60 * mm])))

    # Data quality
    _add_section_title(story, "3. Data Quality")
    quality = analyze_quality(df)
    q_rows = [
        ["Metric", "Value"],
        ["Total cells", str(quality["total_cells"])],
        ["Missing cells", f"{quality['missing_cells']} ({quality['missing_percent']}%)"],
        ["Duplicate rows", str(quality["duplicate_rows"])],
        ["Empty columns", ", ".join(quality["empty_columns"]) or "None"],
    ]
    story.append(_style_table(Table(q_rows, colWidths=[60 * mm, 90 * mm])))
    if quality["issues"]:
        issue_rows = [["Severity", "Issue"]]
        for issue in quality["issues"][:10]:
            issue_rows.append([issue["severity"], issue["message"]])
        story.append(Spacer(1, 6))
        story.append(_style_table(Table(issue_rows, colWidths=[25 * mm, 125 * mm])))

    # Statistics
    _add_section_title(story, "4. Statistics")
    stats = compute_column_statistics(df)
    stat_rows = [["Column", "Type", "Count", "Missing", "Unique", "Mean", "Min", "Max"]]
    for s in stats:
        num = s.get("numeric") or {}
        stat_rows.append([
            s["name"], s["dtype"], str(s["count"]), str(s["missing"]), str(s["unique"]),
            str(num.get("mean", "—")), str(num.get("min", "—")), str(num.get("max", "—")),
        ])
    story.append(_style_table(Table(stat_rows, colWidths=[34 * mm, 18 * mm, 16 * mm, 16 * mm, 16 * mm, 26 * mm, 22 * mm, 22 * mm])))

    # Questions and answers
    analyses = (
        db.query(Analysis)
        .filter(Analysis.dataset_id == dataset.id, Analysis.user_id == user.id)
        .order_by(Analysis.created_at.asc())
        .limit(20)
        .all()
    )
    if analyses:
        _add_section_title(story, "5. Questions & Answers")
        qa_style = ParagraphStyle("QA", parent=styles["Normal"], fontSize=9, spaceAfter=6)
        for a in analyses:
            story.append(Paragraph(f"<b>Q:</b> {a.question}", qa_style))
            story.append(Paragraph(f"<b>A:</b> {a.answer}", qa_style))
            if a.chart_spec:
                png = _render_chart_png(a.chart_spec)
                if png:
                    img = Image(io.BytesIO(png), width=150 * mm, height=75 * mm)
                    story.append(img)
            story.append(Spacer(1, 8))

    doc.build(story)

    report = Report(
        user_id=user.id,
        dataset_id=dataset.id,
        report_name=name,
        stored_filename=stored_filename,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_path(report: Report) -> Path:
    base = (settings.STORAGE_DIR / str(report.user_id) / "reports").resolve()
    resolved = (base / report.stored_filename).resolve()
    if not str(resolved).startswith(str(base)):
        raise ValueError("Invalid report path")
    return resolved