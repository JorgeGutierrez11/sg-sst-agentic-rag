from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from agents.diagnostico_cumplimiento.reporting.upa_scoring_matrix import (
    UPAScoringMatrix,
    UPATableStatus,
)


PAGE_SIZE = landscape(A4)


def build_upa_table_pdf(
    matrix: UPAScoringMatrix,
    output_path: str | Path,
) -> Path:
    """
    Genera la tabla de calificación para UPA de diez (10)
    o menos trabajadores permanentes.

    El PDF representa los tres estándares aplicables y
    conserva una columna de comentario orientativo.
    """

    output = Path(output_path)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    document = SimpleDocTemplate(
        str(output),
        pagesize=PAGE_SIZE,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=(
            "Estándares Mínimos SG-SST - "
            "Unidad de Producción Agropecuaria"
        ),
    )

    title_style = ParagraphStyle(
        "upa_title",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
    )

    subtitle_style = ParagraphStyle(
        "upa_subtitle",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )

    header_style = ParagraphStyle(
        "upa_header",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        alignment=TA_CENTER,
    )

    cell_style = ParagraphStyle(
        "upa_cell",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
    )

    centered_cell_style = ParagraphStyle(
        "upa_centered_cell",
        parent=cell_style,
        alignment=TA_CENTER,
    )

    comment_style = ParagraphStyle(
        "upa_comment",
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        alignment=TA_LEFT,
    )

    story = [
        Paragraph(
            "ESTÁNDARES MÍNIMOS SG-SST",
            title_style,
        ),
        Paragraph(
            (
                "Unidad de Producción Agropecuaria con diez "
                "(10) o menos trabajadores permanentes - "
                "Resolución 0312 de 2019"
            ),
            subtitle_style,
        ),
        Spacer(
            1,
            2 * mm,
        ),
    ]

    data = [
        [
            Paragraph(
                "Estándar mínimo",
                header_style,
            ),
            Paragraph(
                "Valor",
                header_style,
            ),
            Paragraph(
                "Cumple totalmente",
                header_style,
            ),
            Paragraph(
                "Cumple parcialmente",
                header_style,
            ),
            Paragraph(
                "No cumple",
                header_style,
            ),
            Paragraph(
                "No aplica",
                header_style,
            ),
            Paragraph(
                "Calificación",
                header_style,
            ),
            Paragraph(
                "Comentario",
                header_style,
            ),
        ]
    ]

    for row in matrix.rows:
        data.append(
            [
                Paragraph(
                    row.name,
                    cell_style,
                ),
                Paragraph(
                    _format_number(
                        row.maximum_score
                    ),
                    centered_cell_style,
                ),
                Paragraph(
                    _mark(
                        row.table_status
                        == UPATableStatus.COMPLIES_FULLY
                    ),
                    centered_cell_style,
                ),
                Paragraph(
                    _mark(
                        row.table_status
                        == UPATableStatus.COMPLIES_PARTIALLY
                    ),
                    centered_cell_style,
                ),
                Paragraph(
                    _mark(
                        row.table_status
                        == UPATableStatus.DOES_NOT_COMPLY
                    ),
                    centered_cell_style,
                ),
                Paragraph(
                    _mark(
                        row.table_status
                        == UPATableStatus.NOT_APPLICABLE
                    ),
                    centered_cell_style,
                ),
                Paragraph(
                    _format_number(
                        row.score
                    ),
                    centered_cell_style,
                ),
                Paragraph(
                    row.comment,
                    comment_style,
                ),
            ]
        )

    data.append(
        [
            Paragraph(
                "<b>TOTAL</b>",
                header_style,
            ),
            Paragraph(
                "<b>100</b>",
                header_style,
            ),
            "",
            "",
            "",
            "",
            Paragraph(
                (
                    "<b>"
                    + _format_number(
                        matrix.summary.total_score
                    )
                    + "</b>"
                ),
                header_style,
            ),
            "",
        ]
    )

    table = Table(
        data,
        colWidths=[
            68 * mm,
            13 * mm,
            20 * mm,
            21 * mm,
            18 * mm,
            17 * mm,
            20 * mm,
            82 * mm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#D9EAF7"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    colors.HexColor("#666666"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (6, -1),
                    "CENTER",
                ),
                (
                    "BACKGROUND",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#EEEEEE"),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    story.append(
        table
    )

    document.build(
        story
    )

    return output


def _mark(
    selected: bool,
) -> str:
    return "X" if selected else ""


def _format_number(
    value: float,
) -> str:
    if float(value).is_integer():
        return str(
            int(value)
        )

    return (
        f"{value:.2f}"
        .rstrip("0")
        .rstrip(".")
        .replace(".", ",")
    )
