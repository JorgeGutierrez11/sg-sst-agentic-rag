from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)

from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
)
from agents.diagnostico_cumplimiento.reporting.art27_scoring_matrix import (
    Article27ScoringMatrix,
    Article27ScoringRow,
)


PAGE_SIZE = landscape(A3)

LEFT_MARGIN = 12 * mm
RIGHT_MARGIN = 12 * mm
TOP_MARGIN = 16 * mm
BOTTOM_MARGIN = 14 * mm


def build_article27_table_pdf(
    matrix: Article27ScoringMatrix,
    output_path: str | Path | BinaryIO,
) -> Path | BinaryIO:
    """
    Genera un PDF con la Tabla de Valores y Calificación
    del artículo 27 de la Resolución 0312 de 2019.

    La función recibe una matriz ya calculada y puede escribir
    el documento en una ruta física o en un buffer binario.

    No determina:
    - aplicabilidad;
    - cumplimiento;
    - puntajes.

    Su responsabilidad es exclusivamente de presentación.
    """

    if isinstance(output_path, (str, Path)):
        output: Path | BinaryIO = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        document_target = str(output)

    else:
        output = output_path
        document_target = output

    document = SimpleDocTemplate(
        document_target,
        pagesize=PAGE_SIZE,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=(
            "Tabla de Valores y Calificación "
            "- Artículo 27"
        ),
        author="Sistema inteligente de asistencia SG-SST",
    )

    story = []

    styles = _build_styles()

    story.append(
        Paragraph(
            "ESTÁNDARES MÍNIMOS SG-SST",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "TABLA DE VALORES Y CALIFICACIÓN",
            styles["subtitle"],
        )
    )

    story.append(
        Paragraph(
            (
                "Resultado orientativo construido a partir "
                "de la información declarada por la empresa."
            ),
            styles["scope"],
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    table_data, table_style = _build_table(
        matrix=matrix,
        styles=styles,
    )

    table = LongTable(
        table_data,
        colWidths=[
            22 * mm,   # Ciclo
            45 * mm,   # Estándar
            75 * mm,   # Ítem
            13 * mm,   # Valor
            15 * mm,   # Peso
            17 * mm,   # Cumple
            17 * mm,   # No cumple
            17 * mm,   # No aplica
            21 * mm,   # Calificación
            120 * mm,  # Comentario
        ],
        repeatRows=2,
        hAlign="CENTER",
        splitByRow=1,
    )

    table.setStyle(
        table_style
    )

    story.append(table)

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    story.append(
        Paragraph(
            _build_footer_note(matrix),
            styles["note"],
        )
    )

    document.build(
        story,
        onFirstPage=_draw_page_footer,
        onLaterPages=_draw_page_footer,
    )

    return output


def _build_table(
    *,
    matrix: Article27ScoringMatrix,
    styles: dict[str, ParagraphStyle],
) -> tuple[list[list[object]], TableStyle]:
    data: list[list[object]] = [
        [
            Paragraph("CICLO", styles["header"]),
            Paragraph("ESTÁNDAR", styles["header"]),
            Paragraph(
                "ÍTEM DEL ESTÁNDAR",
                styles["header"],
            ),
            Paragraph("Valor", styles["header"]),
            Paragraph(
                "Peso<br/>Porcentual",
                styles["header"],
            ),
            Paragraph(
                "PUNTAJE POSIBLE",
                styles["header"],
            ),
            "",
            "",
            Paragraph(
                "Calificación de la empresa",
                styles["header"],
            ),
            Paragraph(
                "Comentario",
                styles["header"],
            ),
        ],
        [
            "",
            "",
            "",
            "",
            "",
            Paragraph(
                "Cumple<br/>totalmente",
                styles["header_small"],
            ),
            Paragraph(
                "No<br/>cumple",
                styles["header_small"],
            ),
            Paragraph(
                "No<br/>aplica",
                styles["header_small"],
            ),
            "",
            "",
        ],
    ]

    row_metadata: list[
        tuple[
            Article27ScoringRow,
            bool,
            bool,
        ]
    ] = []

    previous_cycle: str | None = None
    previous_standard: str | None = None

    for row in matrix.rows:
        is_cycle_start = (
            row.cycle_id != previous_cycle
        )

        is_standard_start = (
            is_cycle_start
            or row.standard_id != previous_standard
        )

        cycle_text = (
            row.cycle_name
            if is_cycle_start
            else ""
        )

        if is_standard_start:
            standard_text = (
                f"<b>{row.component_name}</b>"
                f"<br/>{row.standard_name}"
            )
            weight_text = _format_number(
                row.weight_percent
            )
        else:
            standard_text = ""
            weight_text = ""

        data.append(
            [
                Paragraph(
                    cycle_text,
                    styles["cycle"],
                ),
                Paragraph(
                    standard_text,
                    styles["standard"],
                ),
                Paragraph(
                    (
                        f"<b>{row.official_item_id}</b> "
                        f"{row.description}"
                    ),
                    styles["cell"],
                ),
                Paragraph(
                    _format_number(
                        row.item_value
                    ),
                    styles["number"],
                ),
                Paragraph(
                    weight_text,
                    styles["number"],
                ),
                Paragraph(
                    "X" if row.complies_fully else "",
                    styles["mark"],
                ),
                Paragraph(
                    "X" if row.does_not_comply else "",
                    styles["mark"],
                ),
                Paragraph(
                    "X" if row.not_applicable else "",
                    styles["mark"],
                ),
                Paragraph(
                    _format_number(
                        row.score
                    ),
                    styles["number"],
                ),
                Paragraph(
                    _display_comment(row),
                    styles["comment"],
                ),
            ]
        )

        row_metadata.append(
            (
                row,
                is_cycle_start,
                is_standard_start,
            )
        )

        previous_cycle = row.cycle_id
        previous_standard = row.standard_id

    data.append(
        [
            Paragraph(
                "<b>TOTALES</b>",
                styles["total"],
            ),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            Paragraph(
                f"<b>{_format_number(matrix.summary.total_score)}</b>",
                styles["total"],
            ),
            Paragraph(
                (
                    "<b>Calificación total sobre 100.</b>"
                ),
                styles["total_comment"],
            ),
        ]
    )

    style_commands: list[tuple] = [
        # -------------------------------------------------
        # Encabezado.
        # -------------------------------------------------
        (
            "SPAN",
            (0, 0),
            (0, 1),
        ),
        (
            "SPAN",
            (1, 0),
            (1, 1),
        ),
        (
            "SPAN",
            (2, 0),
            (2, 1),
        ),
        (
            "SPAN",
            (3, 0),
            (3, 1),
        ),
        (
            "SPAN",
            (4, 0),
            (4, 1),
        ),
        (
            "SPAN",
            (5, 0),
            (7, 0),
        ),
        (
            "SPAN",
            (8, 0),
            (8, 1),
        ),
        (
            "SPAN",
            (9, 0),
            (9, 1),
        ),
        (
            "BACKGROUND",
            (0, 0),
            (-1, 1),
            colors.HexColor("#D9E2F3"),
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 1),
            colors.HexColor("#111827"),
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "ALIGN",
            (0, 0),
            (-1, 1),
            "CENTER",
        ),
        (
            "BOX",
            (0, 0),
            (-1, -1),
            0.65,
            colors.HexColor("#334155"),
        ),
        (
            "GRID",
            (0, 0),
            (-1, 1),
            0.55,
            colors.HexColor("#475569"),
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
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),

        # -------------------------------------------------
        # Líneas verticales para toda la tabla.
        # -------------------------------------------------
        (
            "LINEBEFORE",
            (1, 0),
            (1, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (2, 0),
            (2, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (3, 0),
            (3, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (4, 0),
            (4, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (5, 0),
            (5, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (6, 0),
            (6, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (7, 0),
            (7, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (8, 0),
            (8, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),
        (
            "LINEBEFORE",
            (9, 0),
            (9, -1),
            0.35,
            colors.HexColor("#94A3B8"),
        ),

        # -------------------------------------------------
        # Total.
        # -------------------------------------------------
        (
            "SPAN",
            (0, -1),
            (7, -1),
        ),
        (
            "BACKGROUND",
            (0, -1),
            (-1, -1),
            colors.HexColor("#E2E8F0"),
        ),
        (
            "LINEABOVE",
            (0, -1),
            (-1, -1),
            0.8,
            colors.HexColor("#334155"),
        ),
        (
            "ALIGN",
            (0, -1),
            (8, -1),
            "CENTER",
        ),
    ]

    first_data_row = 2

    for index, metadata in enumerate(
        row_metadata
    ):
        row, is_cycle_start, is_standard_start = (
            metadata
        )

        table_row = first_data_row + index

        # Cada ítem conserva su separación desde la
        # columna "Ítem" hacia la derecha.
        style_commands.append(
            (
                "LINEBELOW",
                (2, table_row),
                (-1, table_row),
                0.25,
                colors.HexColor("#CBD5E1"),
            )
        )

        # Solo se dibuja una división en la columna
        # ESTÁNDAR cuando comienza otro estándar.
        if index > 0 and is_standard_start:
            style_commands.append(
                (
                    "LINEABOVE",
                    (1, table_row),
                    (-1, table_row),
                    0.45,
                    colors.HexColor("#94A3B8"),
                )
            )

        # Solo se dibuja una división completa cuando
        # inicia un nuevo ciclo PHVA.
        if index > 0 and is_cycle_start:
            style_commands.append(
                (
                    "LINEABOVE",
                    (0, table_row),
                    (-1, table_row),
                    0.8,
                    colors.HexColor("#475569"),
                )
            )

        # Fondo muy ligero para filas evaluadas por
        # el Agente 2. Los No Aplica del alcance quedan
        # visualmente neutros.
        if row.requirement_id is not None:
            style_commands.append(
                (
                    "BACKGROUND",
                    (2, table_row),
                    (-1, table_row),
                    colors.HexColor("#F8FAFC"),
                )
            )

    return (
        data,
        TableStyle(style_commands),
    )


def _display_comment(
    row: Article27ScoringRow,
) -> str:
    """
    Obtiene una versión compacta del comentario para la tabla.

    El detalle completo permanece disponible en la matriz
    y en el informe orientativo.
    """

    if row.requirement_id is None:
        return row.comment

    if (
        row.assessment_status
        == DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED
    ):
        return (
            "Cumple según la información declarada "
            "por la empresa."
        )

    if (
        row.assessment_status
        == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
    ):
        detail = row.comment

        marker = (
            "Para efectos de la tabla de calificación"
        )

        if marker in detail:
            detail = detail.split(
                marker,
                1,
            )[0].strip()

        return detail

    if (
        row.assessment_status
        == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
    ):
        comment = row.comment.replace(
            (
                "Las declaraciones recopiladas permiten "
                "identificar al menos una condición "
                "evaluativa no satisfecha."
            ),
            "",
        ).strip()

        comment = comment.replace(
            (
                "La empresa declaró una situación "
                "negativa respecto de: "
            ),
            "Declaración negativa: ",
        )

        return (
            comment
            or "No cumple según la información declarada."
        )

    if (
        row.assessment_status
        == DeclarativeAssessmentStatus.NOT_APPLICABLE
    ):
        return row.comment

    return row.comment


def _build_footer_note(
    matrix: Article27ScoringMatrix,
) -> str:
    return (
        "<b>Nota:</b> La tabla conserva la estructura de "
        "calificación del artículo 27. El resultado se basa "
        "en información declarada y no constituye auditoría "
        "ni verificación documental. Cuando el diagnóstico "
        "interno presenta información insuficiente, el estado "
        "se conserva internamente y, para efectos de esta "
        "tabla, se representa como <b>No cumple</b> con "
        "puntaje cero. "
        f"<b>Puntaje total: "
        f"{_format_number(matrix.summary.total_score)} / 100.</b>"
    )


def _build_styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            name="Art27Title",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            name="Art27Subtitle",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "scope": ParagraphStyle(
            name="Art27Scope",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
        ),
        "header": ParagraphStyle(
            name="Art27Header",
            fontName="Helvetica-Bold",
            fontSize=6.2,
            leading=7.2,
            alignment=TA_CENTER,
        ),
        "header_small": ParagraphStyle(
            name="Art27HeaderSmall",
            fontName="Helvetica-Bold",
            fontSize=5.8,
            leading=6.6,
            alignment=TA_CENTER,
        ),
        "cycle": ParagraphStyle(
            name="Art27Cycle",
            fontName="Helvetica-Bold",
            fontSize=6.1,
            leading=7.2,
            alignment=TA_CENTER,
        ),
        "standard": ParagraphStyle(
            name="Art27Standard",
            fontName="Helvetica",
            fontSize=5.7,
            leading=6.8,
            alignment=TA_LEFT,
        ),
        "cell": ParagraphStyle(
            name="Art27Cell",
            fontName="Helvetica",
            fontSize=5.8,
            leading=6.9,
            alignment=TA_LEFT,
        ),
        "number": ParagraphStyle(
            name="Art27Number",
            fontName="Helvetica",
            fontSize=6.2,
            leading=7.2,
            alignment=TA_CENTER,
        ),
        "mark": ParagraphStyle(
            name="Art27Mark",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
        ),
        "comment": ParagraphStyle(
            name="Art27Comment",
            fontName="Helvetica",
            fontSize=5.6,
            leading=6.7,
            alignment=TA_LEFT,
        ),
        "total": ParagraphStyle(
            name="Art27Total",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
        ),
        "total_comment": ParagraphStyle(
            name="Art27TotalComment",
            fontName="Helvetica-Bold",
            fontSize=6.2,
            leading=7.2,
            alignment=TA_LEFT,
        ),
        "note": ParagraphStyle(
            name="Art27Note",
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#334155"),
        ),
    }


def _format_number(
    value: float,
) -> str:
    if float(value).is_integer():
        return str(
            int(value)
        )

    text = (
        f"{value:.2f}"
        .rstrip("0")
        .rstrip(".")
    )

    return text.replace(
        ".",
        ",",
    )


def _draw_page_footer(
    canvas,
    document,
) -> None:
    canvas.saveState()

    page_width, _ = PAGE_SIZE

    canvas.setFont(
        "Helvetica",
        6.5,
    )

    canvas.setFillColor(
        colors.HexColor("#64748B")
    )

    canvas.drawString(
        LEFT_MARGIN,
        7 * mm,
        (
            "Resolución 0312 de 2019 - "
            "Artículo 27 - Resultado orientativo"
        ),
    )

    canvas.drawRightString(
        page_width - RIGHT_MARGIN,
        7 * mm,
        f"Página {document.page}",
    )

    canvas.restoreState()
