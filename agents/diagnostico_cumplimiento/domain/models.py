from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CompanyProfile(BaseModel):
    """
    Perfil mínimo de la empresa necesario para determinar
    los Estándares Mínimos aplicables al diagnóstico.

    El alcance actual del Agente 2 está limitado a empresas
    clasificadas en riesgo I.
    """

    worker_count: int = Field(
        gt=0,
        description="Número actual de trabajadores de la empresa.",
    )

    risk_class: RiskClass = Field(
        description=(
            "Clase de riesgo declarada por la empresa. "
            "El Agente 2 únicamente realiza diagnósticos para riesgo I."
        ),
    )

    economic_activity: str | None = Field(
        default=None,
        description="Actividad económica declarada por la empresa.",
    )

    ciiu_code: str | None = Field(
        default=None,
        description="Código CIIU de la actividad económica, si está disponible.",
    )

    is_agricultural_production_unit: bool = Field(
        default=False,
        description=(
            "Indica si la empresa corresponde a una Unidad de "
            "Producción Agropecuaria (UPA)."
        ),
    )

    permanent_worker_count: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Número de trabajadores permanentes de la UPA. "
            "Se utiliza para determinar el paquete normativo "
            "aplicable cuando la empresa es una UPA."
        ),
    )

    @model_validator(mode="after")
    def validate_agricultural_profile(self) -> "CompanyProfile":
        if (
            self.is_agricultural_production_unit
            and self.permanent_worker_count is None
        ):
            raise ValueError(
                "Una Unidad de Producción Agropecuaria debe informar "
                "la cantidad de trabajadores permanentes."
            )

        if (
            self.permanent_worker_count is not None
            and self.permanent_worker_count > self.worker_count
        ):
            raise ValueError(
                "La cantidad de trabajadores permanentes no puede "
                "ser mayor que la cantidad total de trabajadores."
            )

        return self


class NormativeSource(BaseModel):
    """
    Fuente oficial que sustenta un requisito utilizado
    durante la autoevaluación.
    """

    regulation: str = Field(
        min_length=1,
        description="Nombre de la norma.",
    )

    article: str = Field(
        min_length=1,
        description="Artículo o ubicación normativa del requisito.",
    )

    official_url: str = Field(
        min_length=1,
        description="URL de la fuente oficial.",
    )


class ApplicabilityRule(BaseModel):
    """
    Define para qué perfiles empresariales aplica un requisito.

    La evaluación de esta regla será responsabilidad del
    motor determinístico de aplicabilidad.
    """

    risk_classes: list[Literal["I"]] = Field(
        min_length=1,
        description="Clases de riesgo para las que aplica el requisito.",
    )

    worker_count_min: int = Field(
        ge=1,
        description="Cantidad mínima de trabajadores.",
    )

    worker_count_max: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Cantidad máxima de trabajadores. "
            "None indica que no existe límite superior definido en esta regla."
        ),
    )

    @model_validator(mode="after")
    def validate_worker_range(self) -> "ApplicabilityRule":
        if (
            self.worker_count_max is not None
            and self.worker_count_max < self.worker_count_min
        ):
            raise ValueError(
                "worker_count_max must be greater than or equal to "
                "worker_count_min"
            )

        return self