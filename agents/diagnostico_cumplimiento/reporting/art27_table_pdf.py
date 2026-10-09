from __future__ import annotations

from pathlib import Path
from html import escape
from typing import BinaryIO

from datetime import datetime
from zoneinfo import ZoneInfo
from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
)
from agents.diagnostico_cumplimiento.reporting.normative_gap_analysis import (
    NormativeGapAnalysis,
)

from agents.diagnostico_cumplimiento.reporting.report_context import (
    CompanyReportInfo,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    BaseDocTemplate,
    Frame,
    PageTemplate,
    NextPageTemplate,
)



from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
)
from agents.diagnostico_cumplimiento.reporting.art27_scoring_matrix import (
    Article27ScoringMatrix,
    Article27ScoringRow,
)


PAGE_WIDTH = 349 * mm
PAGE_HEIGHT = 297 * mm
FIRST_PAGE_HEIGHT = 195 * mm
FIRST_PAGE_SIZE = (
    PAGE_WIDTH,
    FIRST_PAGE_HEIGHT,
)
PAGE_SIZE = (
    PAGE_WIDTH,
    PAGE_HEIGHT,
)

FINAL_PAGE_SIZE = FIRST_PAGE_SIZE

LEFT_MARGIN = 12 * mm
RIGHT_MARGIN = 12 * mm
TOP_MARGIN = 16 * mm
BOTTOM_MARGIN = 14 * mm

BRAND_GREEN = colors.HexColor("#00E699")
BRAND_GREEN_SOFT = colors.HexColor("#D9FFF2")

TEXT_PRIMARY = colors.HexColor("#0F172A")
#TEXT_SECONDARY = colors.HexColor("#3D4858")
TEXT_SECONDARY = colors.HexColor("#0F172A")

SURFACE = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#E2E8F0")

SUCCESS_BG = colors.HexColor("#DCFCE7")
SUCCESS_TEXT = colors.HexColor("#166534")

WARNING_BG = colors.HexColor("#FEF3C7")
WARNING_TEXT = colors.HexColor("#92400E")

CRITICAL_BG = colors.HexColor("#FEE2E2")
CRITICAL_TEXT = colors.HexColor("#991B1B")


TABLE_MARK_COMPLIES = "#16A34A"
TABLE_MARK_DOES_NOT_COMPLY = "#DC2626"
TABLE_MARK_NOT_APPLICABLE = "#64748B"

# ---------------------------------------------------------
# Paleta visual de tablas
# Cambiar estos valores modifica las tablas sin tocar
# su estructura ni la lógica del reporte.
# ---------------------------------------------------------

TABLE_HEADER_BG = BRAND_GREEN_SOFT
TABLE_HEADER_TEXT = TEXT_PRIMARY

TABLE_TOTAL_BG = colors.HexColor("#ECFDF5")

TABLE_BORDER_STRONG = colors.HexColor("#64748B")
TABLE_BORDER = colors.HexColor("#CBD5E1")

# Estados visuales de la tabla de brechas
GAP_NONCOMPLIANCE_COLOR = "#DC2626"
GAP_NONCOMPLIANCE_BG = colors.HexColor("#FEF2F2")

GAP_INSUFFICIENT_COLOR = "#D97706"
GAP_INSUFFICIENT_BG = colors.HexColor("#FFF7ED")

def _format_orientative_action(
    value: str,
) -> str:
    lines = [
        line.strip()
        for line in value.splitlines()
        if line.strip()
    ]

    return "<br/>".join(
        escape(line)
        for line in lines
    )

def _build_normative_criteria(
    *,
    matrix: Article27ScoringMatrix,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    content: list[object] = [
        Paragraph(
            "CRITERIOS NORMATIVOS - RESOLUCIÓN 0312 DE 2019",
            styles["section_title"],
        ),
        Spacer(
            1,
            3 * mm,
        ),

        Paragraph(
            (
                "<b>Artículo 26 - Autoevaluación de los "
                "Estándares Mínimos.</b> "
                "Las empresas deben realizar anualmente la "
                "autoevaluación de los Estándares Mínimos "
                "del SG-SST mediante la Tabla de Valores y "
                "Calificación, y formular las acciones de "
                "mejora correspondientes."
            ),
            styles["summary_explanation"],
        ),

        Spacer(
            1,
            4 * mm,
        ),

        Paragraph(
            (
                "<b>Artículo 27 - Tabla de Valores y "
                "Calificación.</b> "
                "Establece los valores y la forma de "
                "calificar los Estándares Mínimos del SG-SST."
            ),
            styles["summary_explanation"],
        ),
    ]

    if matrix.catalog_id in {
        "res0312_riesgo_i_1_10_general",
        "res0312_riesgo_i_11_50",
    }:
        content.extend(
            [
                Spacer(
                    1,
                    2 * mm,
                ),
                Paragraph(
                    (
                        "<b>Artículo 27 - Ítems “No aplica”.</b> "
                        "Para empresas de menos de cincuenta "
                        "(50) trabajadores clasificadas en "
                        "riesgo I, II o III, los ítems que no "
                        "resulten aplicables reciben el "
                        "porcentaje máximo correspondiente en "
                        "la columna “No Aplica”."
                    ),
                    styles["summary_explanation"],
                ),
            ]
        )

    content.extend(
        [
            Spacer(
                1,
                4 * mm,
            ),

            Paragraph(
                (
                    "<b>Artículo 28 - Interpretación "
                    "del resultado.</b>"
                ),
                styles["summary_explanation"],
            ),

            Spacer(
                1,
                2 * mm,
            ),

            Paragraph(
                "Menor de 60 %: <b>CRÍTICO</b>",
                styles["summary_explanation"],
            ),
            Paragraph(
                (
                    "Entre 60 % y 85 %: "
                    "<b>MODERADAMENTE ACEPTABLE</b>"
                ),
                styles["summary_explanation"],
            ),
            Paragraph(
                "Mayor de 85 %: <b>ACEPTABLE</b>",
                styles["summary_explanation"],
            ),

            Spacer(1, 3 * mm),


            Paragraph(
                "REGISTRO ANUAL - CIRCULAR 0027 DE 2026",
                styles["section_title"],
            ),
            
            Spacer(1, 3 * mm),

            Paragraph(
                "La Circular 0027 del 26 de febrero de 2026 reitera el deber de realizar anualmente la"
                " autoevaluación de los Estándares Mínimos del SG-SST y registrar la autoevaluación y el respectivo"
                " plan de mejoramiento en la aplicación dispuesta para tal fin. Para la vigencia 2026, estableció el"
                " registro de la autoevaluación correspondiente al año 2025.",
                styles["summary_explanation"],
            ),
        ]
    )

    
    return content

def _build_card(
    content,
    *,
    width: float,
) -> Table:
    card = Table(
        [[content]],
        colWidths=[width],
        hAlign="LEFT",
    )

    card.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.white,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    BORDER,
                ),
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    2.5,
                    BRAND_GREEN,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    11,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    11,
                ),
            ]
        )
    )

    return card

def _build_company_information(
    *,
    company_info: CompanyReportInfo,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    company_name = (
        company_info.company_name.strip()
        if company_info.company_name
        and company_info.company_name.strip()
        else "No informada"
    )

    data = [
        [
            Paragraph(
                "Empresa",
                styles["summary_label"],
            ),
            Paragraph(
                escape(company_name),
                styles["summary_value"],
            ),
        ],
        [
            Paragraph(
                "Trabajadores declarados",
                styles["summary_label"],
            ),
            Paragraph(
                str(company_info.worker_count),
                styles["summary_value"],
            ),
        ],
        [
            Paragraph(
                "Clase de riesgo declarada",
                styles["summary_label"],
            ),
            Paragraph(
                company_info.risk_class,
                styles["summary_value"],
            ),
        ],
        [
            Paragraph(
                "Artículo aplicable",
                styles["summary_label"],
            ),
            Paragraph(
                (
                    f"Artículo {company_info.requirements_article} "
                    f"- {escape(company_info.norm)}"
                ),
                styles["summary_value"],
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[
            62 * mm,
            82 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return [
        Paragraph(
            "INFORMACIÓN DE LA EMPRESA",
            styles["section_title"],
        ),
        Spacer(
            1,
            3 * mm,
        ),
        table,
        Spacer(
            1,
            4 * mm,
        ),
        Paragraph(
            (
                "Los datos presentados corresponden al perfil "
                "utilizado para determinar los Estándares "
                "Mínimos aplicables al diagnóstico."
            ),
            styles["summary_explanation"],
        ),
    ]

def _build_first_page_layout(
    *,
    matrix: Article27ScoringMatrix,
    company_info: CompanyReportInfo,
    generated_at: datetime,
    styles: dict[str, ParagraphStyle],
) -> Table:
    summary_block = _build_card(
        _build_evaluation_summary(
            matrix=matrix,
            styles=styles,
        ),
        width=160 * mm,
    )

    company_block = _build_card(
        _build_company_information(
            company_info=company_info,
            styles=styles,
        ),
        width=157 * mm,
    )

    score_block = _build_score_summary(
        matrix=matrix,
        generated_at=generated_at,
        styles=styles,
    )

    layout = Table(
        [
            [
                summary_block,
                "",
                company_block,
            ],
            [
                score_block,
                "",
                "",
            ],
        ],
        colWidths=[
            160 * mm,
            8 * mm,
            157 * mm,
        ],
        hAlign="CENTER",
    )

    layout.setStyle(
        TableStyle(
            [
                (
                    "SPAN",
                    (0, 1),
                    (2, 1),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )
    return layout

def _build_report_information(
    *,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    

    official_resolution_url = (
        "https://www1.funcionpublica.gov.co/"
        "documents/34645357/34703621/"
        "Resolucion_0312_de_2019.pdf/"
        "3c93008d-dd8e-8b0d-e5ea-ec6699db86e7"
    )

    return [
        Paragraph(
            "MARCO DE INTERPRETACIÓN DEL INFORME",
            styles["section_title"],
        ),
        Spacer(
            1,
            3 * mm,
        ),
        Paragraph(
            (
                "<b>Alcance del diagnóstico.</b> "
                "Este informe se construye a partir de la "
                "información declarada durante la evaluación. "
                "No constituye auditoría, verificación oficial, "
                "certificación de cumplimiento ni asesoría "
                "jurídica o profesional en Seguridad y Salud "
                "en el Trabajo."
            ),
            styles["summary_explanation"],
        ),
        Spacer(
            1,
            3 * mm,
        ),
        Paragraph(
            (
                "<b>Fuente normativa oficial.</b> "
                "Resolución 0312 de 2019 del Ministerio del "
                "Trabajo - Por la cual se definen los "
                "Estándares Mínimos del Sistema de Gestión "
                "de la Seguridad y Salud en el Trabajo SG-SST. "
                f'<link href="{official_resolution_url}" '
                'color="#2563EB">'
                "Consultar resolución oficial"
                "</link>."
            ),
            styles["summary_explanation"],
        ),
        
    ]

def _gap_status_label(
    status: DeclarativeAssessmentStatus,
) -> str:
    if (
        status
        == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
    ):
        return "No cumple según declaración"

    if (
        status
        == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
    ):
        return "Información insuficiente"

    raise ValueError(
        f"Estado no válido para una brecha: {status}"
    )

def _gap_status_visual(
    status: DeclarativeAssessmentStatus,
) -> tuple[str, colors.Color]:
    if (
        status
        == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
    ):
        return (
            (
                f'<font color="{GAP_NONCOMPLIANCE_COLOR}">'
                "<b>●</b>"
                "</font> "
                "<b>No cumple según declaración</b>"
            ),
            GAP_NONCOMPLIANCE_BG,
        )

    if (
        status
        == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
    ):
        return (
            (
                f'<font color="{GAP_INSUFFICIENT_COLOR}">'
                "<b>●</b>"
                "</font> "
                "<b>Información insuficiente</b>"
            ),
            GAP_INSUFFICIENT_BG,
        )

    raise ValueError(
        f"Estado no válido para una brecha: {status}"
    )

def _format_gap_sources(finding) -> str:
    return "<br/>".join(
        (
            f"{escape(source.norm)}, "
            f"{escape(source.reference)}"
        )
        for source in finding.sources
    )

def _build_normative_gap_table(
    gap_analysis: NormativeGapAnalysis,
    styles: dict[str, ParagraphStyle],
) -> LongTable | Paragraph:
    if not gap_analysis.findings:
        return Paragraph(
            (
                "No se identificaron requisitos con estado "
                "<b>No cumple según declaración</b> o "
                "<b>Información insuficiente</b>."
            ),
            styles["cell"],
        )

    data: list[list[object]] = [
        [
            Paragraph(
                "ESTADO",
                styles["header"],
            ),
            Paragraph(
                "REQUISITO EVALUADO",
                styles["header"],
            ),
            Paragraph(
                "ACCIÓN ORIENTATIVA",
                styles["header"],
            ),
            Paragraph(
                "FUENTE",
                styles["header"],
            ),
        ]
    ]

    status_backgrounds: list[
        tuple[int, colors.Color]
    ] = []

    for finding in gap_analysis.findings:
        status_html, status_background = _gap_status_visual(
            finding.status
        )

        row_index = len(data)

        status_backgrounds.append(
            (
                row_index,
                status_background,
            )
        )

        requirement_label = (
            f"<b>{escape(finding.official_item_id)}</b><br/>"
            if finding.official_item_id
            else ""
        )

        requirement_label += escape(
            finding.requirement_name
        )

        data.append(
            [
                Paragraph(
                    status_html,
                    styles["cell"],
                ),
                Paragraph(
                    requirement_label,
                    styles["gap_requirement"],
                ),
                Paragraph(
                    _format_orientative_action(
                        finding.orientative_action
                    ),
                    styles["gap_action"],
                ),
                Paragraph(
                    _format_gap_sources(
                        finding
                    ),
                    styles["cell"],
                ),
            ]
        )

    # ---------------------------------------------------------
    # Nota metodológica al final de la tabla.
    # ---------------------------------------------------------

    note_row_index = len(data)

    data.append(
        [
            Paragraph(
                (
                    "<b>Nota:</b> Las acciones orientativas se "
                    "elaboran a partir del estado del requisito, "
                    "la información declarada por la empresa, "
                    "el criterio normativo aplicable y su método "
                    "de verificación."
                ),
                styles["note"],
            ),
            "",
            "",
            "",
        ]
    )

    table = LongTable(
        data,
        colWidths=[
            32 * mm,   # Estado
            66 * mm,   # Requisito evaluado
            188 * mm,  # Acción orientativa
            39 * mm,   # Fuente
        ],
        repeatRows=1,
        hAlign="CENTER",
        splitByRow=1,
    )

    status_style_commands = [
        (
            "BACKGROUND",
            (0, row_index),
            (0, row_index),
            background,
        )
        for row_index, background in status_backgrounds
    ]

    table.setStyle(
        TableStyle(
            [
                # -------------------------------------------------
                # Encabezado.
                # -------------------------------------------------
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    TABLE_HEADER_BG,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, -1),
                    TEXT_PRIMARY,
                ),

                # -------------------------------------------------
                # Contenido.
                # -------------------------------------------------
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    BORDER,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, note_row_index - 1),
                    0.35,
                    BORDER,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),

                # -------------------------------------------------
                # Colores semánticos de ESTADO.
                # -------------------------------------------------
                *status_style_commands,

                # -------------------------------------------------
                # Nota metodológica.
                # -------------------------------------------------
                (
                    "SPAN",
                    (0, note_row_index),
                    (-1, note_row_index),
                ),
                (
                    "BACKGROUND",
                    (0, note_row_index),
                    (-1, note_row_index),
                    colors.HexColor("#F8FAFC"),
                ),
                (
                    "LINEABOVE",
                    (0, note_row_index),
                    (-1, note_row_index),
                    0.6,
                    BORDER,
                ),
                (
                    "TOPPADDING",
                    (0, note_row_index),
                    (-1, note_row_index),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, note_row_index),
                    (-1, note_row_index),
                    8,
                ),
            ]
        )
    )

    return table

def _build_final_reference_page(
    *,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    return [
        Paragraph(
            "REFERENCIAS NORMATIVAS Y ALCANCE DEL INFORME",
            styles["title"],
        ),
        Paragraph(
            "Información complementaria del diagnóstico",
            styles["subtitle"],
        ),
        Spacer(
            1,
            6 * mm,
        ),

        # -----------------------------------------------------
        # Resolución 0312 de 2019
        # -----------------------------------------------------

        _build_card(
            [
                Paragraph(
                    "CRITERIOS NORMATIVOS — RESOLUCIÓN 0312 DE 2019",
                    styles["section_title"],
                ),
                Spacer(
                    1,
                    3 * mm,
                ),
                Paragraph(
                    (
                        "<b>Artículo 26.</b> "
                        "La empresa debe realizar anualmente la "
                        "autoevaluación de los Estándares Mínimos "
                        "y formular las acciones de mejora "
                        "correspondientes."
                    ),
                    styles["summary_explanation"],
                ),
                Spacer(
                    1,
                    2 * mm,
                ),
                Paragraph(
                    (
                        "<b>Artículo 27.</b> "
                        "La Tabla de Valores y Calificación define "
                        "la asignación del puntaje. Para empresas de "
                        "menos de 50 trabajadores clasificadas en "
                        "riesgo I, II o III, los ítems no aplicables "
                        "reciben el porcentaje máximo correspondiente."
                    ),
                    styles["summary_explanation"],
                ),
                Spacer(
                    1,
                    2 * mm,
                ),
                Paragraph(
                    (
                        "<b>Artículo 28.</b> "
                        "Menor de 60 %: <b>CRÍTICO</b> · "
                        "Entre 60 % y 85 %: "
                        "<b>MODERADAMENTE ACEPTABLE</b> · "
                        "Mayor de 85 %: <b>ACEPTABLE</b>."
                    ),
                    styles["summary_explanation"],
                ),
            ],
            width=325 * mm,
        ),

        Spacer(
            1,
            5 * mm,
        ),

        # -----------------------------------------------------
        # Circular 0027 de 2026
        # -----------------------------------------------------

        _build_card(
            [
                Paragraph(
                    "REGISTRO ANUAL — CIRCULAR 0027 DE 2026",
                    styles["section_title"],
                ),
                Spacer(
                    1,
                    3 * mm,
                ),
                Paragraph(
                    (
                        "La Circular 0027 de 2026 reitera el registro "
                        "anual de la autoevaluación de los Estándares "
                        "Mínimos y del respectivo plan de mejoramiento. "
                        "Para la vigencia 2026, corresponde registrar "
                        "la autoevaluación del año 2025."
                    ),
                    styles["summary_explanation"],
                ),
            ],
            width=325 * mm,
        ),

        Spacer(
            1,
            5 * mm,
        ),

        # -----------------------------------------------------
        # Alcance
        # -----------------------------------------------------

        _build_card(
            [
                Paragraph(
                    "MARCO DE INTERPRETACIÓN DEL INFORME",
                    styles["section_title"],
                ),
                Spacer(
                    1,
                    3 * mm,
                ),
                Paragraph(
                    (
                        "Este informe tiene carácter orientativo y "
                        "no constituye auditoría, certificación de "
                        "cumplimiento ni verificación documental del "
                        "SG-SST. Cuando corresponda, los resultados "
                        "deben contrastarse con los soportes y las "
                        "condiciones reales de la empresa."
                    ),
                    styles["summary_explanation"],
                ),
            ],
            width=325 * mm,
        ),
    ]

def build_article27_table_pdf(
    matrix: Article27ScoringMatrix,
    output_path: str | Path | BinaryIO,
    *,
    gap_analysis: NormativeGapAnalysis | None = None,
    company_info: CompanyReportInfo | None = None,
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

    if company_info is None:
        raise ValueError(
            "Company report information is required "
            "to generate the diagnostic report."
        )
    generated_at = datetime.now(
        ZoneInfo("America/Bogota")
    )
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

    document = BaseDocTemplate(
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

    first_page_frame = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
        FIRST_PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
        id="first_page_frame",
    )

    later_pages_frame = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
        PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
        id="later_pages_frame",
    )

    final_page_frame = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
        FIRST_PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN,
        id="final_page_frame",
    )

    document.addPageTemplates(
        [
            PageTemplate(
                id="first_page",
                frames=[first_page_frame],
                pagesize=FIRST_PAGE_SIZE,
                onPage=_draw_page_footer,
            ),
            PageTemplate(
                id="later_pages",
                frames=[later_pages_frame],
                pagesize=PAGE_SIZE,
                onPage=_draw_page_footer,
            ),
            PageTemplate(
                id="final_page",
                frames=[final_page_frame],
                pagesize=FINAL_PAGE_SIZE,
                onPage=_draw_page_footer,
            ),
        ]
    )

    story = []

    styles = _build_styles()

    story.append(
        Paragraph(
            "INFORME ORIENTATIVO DE DIAGNÓSTICO SG-SST",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Resumen del diagnóstico",
            styles["subtitle"],
        )
    )

    story.append(
        Paragraph(
            (
                "Basado en la información declarada "
                "por la empresa."
            ),
            styles["scope"],
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    story.append(
        _build_first_page_layout(
            matrix=matrix,
            company_info=company_info,
            generated_at=generated_at,
            styles=styles,
        )
    )

    story.append(
        NextPageTemplate("later_pages")
    )

    story.append(
        PageBreak()
    )

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
            "Artículo 27 - Resolución 0312 de 2019",
            styles["scope"],
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
            24 * mm,    # Ciclo
            64 * mm,    # Estándar
            110 * mm,   # Ítem del estándar
            15 * mm,    # Valor
            18 * mm,    # Peso porcentual
            21 * mm,    # Cumple totalmente
            21 * mm,    # No cumple
            21 * mm,    # No aplica
            31 * mm,    # Calificación de la empresa
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

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "BRECHAS IDENTIFICADAS",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "ASPECTOS QUE REQUIEREN ATENCIÓN",
            styles["subtitle"],
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    if gap_analysis is not None:
        story.append(
            _build_normative_gap_table(
                gap_analysis,
                styles,
            )
        )

        story.append(
            NextPageTemplate("final_page")
        )

        story.append(
            PageBreak()
        )

        story.extend(
            _build_final_reference_page(
                styles=styles,
            )
        )

    document.build(story)

    return output

def _build_evaluation_summary(
    *,
    matrix: Article27ScoringMatrix,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    summary = matrix.summary

    data = [
        [
            Paragraph(
                "Evaluación aplicable",
                styles["summary_label"],
            ),
            Paragraph(
                matrix.evaluation_scope,
                styles["summary_value"],
            ),
        ],
        [
            Paragraph(
                "Base normativa",
                styles["summary_label"],
            ),
            Paragraph(
                "Resolución 0312 de 2019",
                styles["summary_value"],
            ),
        ],
        [
            Paragraph(
                "Requisitos evaluados",
                styles["summary_label"],
            ),
            Paragraph(
                str(summary.evaluated_items),
                styles["summary_number"],
            ),
        ],
        [
            Paragraph(
                "Cumple según declaración",
                styles["summary_label"],
            ),
            Paragraph(
                str(summary.complies_items),
                styles["summary_number"],
            ),
        ],
        [
            Paragraph(
                "No cumple según declaración",
                styles["summary_label"],
            ),
            Paragraph(
                str(summary.does_not_comply_items),
                styles["summary_number"],
            ),
        ],
        [
            Paragraph(
                "Información insuficiente",
                styles["summary_label"],
            ),
            Paragraph(
                str(summary.insufficient_information_items),
                styles["summary_number"],
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[
            65 * mm,
            115 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
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
            ]
        )
    )

    return [
        Paragraph(
            "RESUMEN DE EVALUACIÓN",
            styles["section_title"],
        ),
        Spacer(
            1,
            3 * mm,
        ),
        table,
        Spacer(
            1,
            4 * mm,
        ),
        
    ]

def _build_score_summary(
    *,
    matrix: Article27ScoringMatrix,
    generated_at: datetime,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    summary = matrix.summary
    rating = summary.article28_rating.value

    if rating == "ACEPTABLE":
        dot_color = "#16A34A"
    elif rating == "MODERADAMENTE ACEPTABLE":
        dot_color = "#D97706"
    else:
        dot_color = "#DC2626"

    score_card = Table(
        [
            [
                Paragraph(
                    "PUNTAJE OBTENIDO",
                    styles["result_eyebrow"],
                ),
            ],
            [
                Paragraph(
                    (
                        f"<b>{_format_number(summary.total_score)}"
                        " / 100</b>"
                    ),
                    styles["score_big"],
                ),
            ],
            [
                Paragraph(
                    "Tabla de Valores y Calificación",
                    styles["result_caption"],
                ),
            ],
        ],
        colWidths=[101 * mm],
    )

    score_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    rating_card = Table(
        [
            [
                Paragraph(
                    "VALORACIÓN ARTÍCULO 28",
                    styles["result_eyebrow"],
                ),
            ],
            [
                Paragraph(
                    (
                        f'<font color="{dot_color}">●</font> '
                        f"<b>{rating}</b>"
                    ),
                    styles["rating_status"],
                ),
            ],
            [
                Paragraph(
                    "Según la Resolución 0312 de 2019",
                    styles["result_caption"],
                ),
            ],
            
        ],
        colWidths=[107 * mm],
    )

    rating_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    date_card = Table(
        [
            [
                Paragraph(
                    "FECHA DE EVALUACIÓN",
                    styles["result_eyebrow"],
                ),
            ],
            [
                Paragraph(
                    (
                        f"<b>{generated_at.strftime('%d/%m/%Y · %H:%M')}</b>"
                    ),
                    styles["score_big"],
                ),
            ],
            [
                Paragraph(
                    "Fecha de generación del diagnóstico",
                    styles["result_caption"],
                ),
            ],
        ],
        colWidths=[101 * mm],
    )

    date_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    indicators = Table(
        [
            [
                score_card,
                "",
                rating_card,
                "",
                date_card,
            ]
        ],
        colWidths=[
            101 * mm,
            8 * mm,
            107 * mm,
            8 * mm,
            101 * mm,
        ],
        hAlign="CENTER",
    )

    indicators.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [
        Spacer(1, 3 * mm),
        Paragraph(
            "RESULTADO DE LA CALIFICACIÓN",
            styles["section_title"],
        ),
        Spacer(1, 3 * mm),
        indicators,
    ]

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
                    (
                        f'<font color="{TABLE_MARK_COMPLIES}">'
                        "<b>X</b>"
                        "</font>"
                        if row.complies_fully
                        else ""
                    ),
                    styles["mark"],
                ),
                Paragraph(
                    (
                        f'<font color="{TABLE_MARK_DOES_NOT_COMPLY}">'
                        "<b>X</b>"
                        "</font>"
                        if row.does_not_comply
                        else ""
                    ),
                    styles["mark"],
                ),
                Paragraph(
                    (
                        f'<font color="{TABLE_MARK_NOT_APPLICABLE}">'
                        "<b>X</b>"
                        "</font>"
                        if row.not_applicable
                        else ""
                    ),
                    styles["mark"],
                ),
                Paragraph(
                    _format_number(
                        row.score
                    ),
                    styles["number"],
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
            "BACKGROUND",
            (0, 0),
            (-1, 1),
            TABLE_HEADER_BG,
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 1),
            TABLE_HEADER_TEXT,
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
            TABLE_TOTAL_BG,
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
            name="Title",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
            spaceAfter=4,
        ),

        "subtitle": ParagraphStyle(
            name="Subtitle",
            fontName="Helvetica",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            textColor=TEXT_SECONDARY,
            spaceAfter=3,
        ),

        "scope": ParagraphStyle(
            name="Scope",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=TEXT_SECONDARY,
        ),

        "header": ParagraphStyle(
            name="Art27Header",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "header_small": ParagraphStyle(
            name="Art27HeaderSmall",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "cycle": ParagraphStyle(
            name="Art27Cycle",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "standard": ParagraphStyle(
            name="Art27Standard",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "cell": ParagraphStyle(
            name="Art27Cell",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=TEXT_PRIMARY,
        ),

        "gap_requirement": ParagraphStyle(
            name="GapRequirement",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "number": ParagraphStyle(
            name="Art27Number",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "mark": ParagraphStyle(
            name="Art27Mark",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "total": ParagraphStyle(
            name="Art27Total",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "note": ParagraphStyle(
            name="Art27Note",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#334155"),
        ),
        "section_title": ParagraphStyle(
            name="SectionTitle",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
            spaceAfter=2,
        ),

        "summary_label": ParagraphStyle(
            name="SummaryLabel",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_SECONDARY,
        ),

        "summary_value": ParagraphStyle(
            name="SummaryValue",
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "summary_number": ParagraphStyle(
            name="SummaryNumber",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "summary_explanation": ParagraphStyle(
            name="SummaryExplanation",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=TEXT_SECONDARY,
            spaceAfter=4,
        ),
        "score_label": ParagraphStyle(
            name="ScoreLabel",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_SECONDARY,
        ),

        "score_value": ParagraphStyle(
            name="ScoreValue",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "score_big": ParagraphStyle(
            name="ScoreBig",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "score_badge": ParagraphStyle(
            name="ScoreBadge",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=TEXT_PRIMARY,
        ),

        "result_eyebrow": ParagraphStyle(
            name="ResultEyebrow",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_SECONDARY,
        ),

        "result_caption": ParagraphStyle(
            name="ResultCaption",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_SECONDARY,
        ),

        "rating_big": ParagraphStyle(
            name="RatingBig",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "rating_status": ParagraphStyle(
            name="RatingStatus",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
        ),

        "gap_action": ParagraphStyle(
            name="GapAction",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_PRIMARY,
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

    page_width, _ = canvas._pagesize

    footer_y = 7 * mm

    canvas.setFont(
        "Helvetica",
        8,
    )

    canvas.setFillColor(
        colors.HexColor("#64748B")
    )

    # Información normativa
    canvas.drawString(
        LEFT_MARGIN,
        footer_y,
        (
            "Resolución 0312 de 2019 - "
            "Artículo 27 - Resultado orientativo"
        ),
    )

    # Marca y enlace
    brand_text = "Generado por NormIA · Visítanos en "
    link_text = "normia.com"

    brand_x = page_width / 2

    brand_width = canvas.stringWidth(
        brand_text,
        "Helvetica",
        8,
    )

    link_width = canvas.stringWidth(
        link_text,
        "Helvetica",
        8,
    )

    total_width = brand_width + link_width
    start_x = brand_x - (total_width / 2)

    canvas.drawString(
        start_x,
        footer_y,
        brand_text,
    )

    link_x = start_x + brand_width

    canvas.setFillColor(
        BRAND_GREEN
    )

    canvas.drawString(
        link_x,
        footer_y,
        link_text,
    )

    canvas.linkURL(
        "https://normia.com",
        (
            link_x,
            footer_y - 1,
            link_x + link_width,
            footer_y + 7,
        ),
        relative=0,
        thickness=0,
    )

    # Número de página
    canvas.setFillColor(
        colors.HexColor("#64748B")
    )

    canvas.drawRightString(
        page_width - RIGHT_MARGIN,
        footer_y,
        f"Página {document.page}",
    )

    canvas.restoreState()
