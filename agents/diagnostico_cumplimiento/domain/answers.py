
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


class QuestionAnswer(BaseModel):
    """
    Registra la respuesta original del usuario a una pregunta.

    No interpreta la respuesta ni determina si el requisito
    normativo se cumple.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(
        min_length=1,
        description="Identificador de la variante del requisito evaluado.",
    )

    question_id: str = Field(
        min_length=1,
        description="Identificador de la pregunta respondida.",
    )

    raw_answer: StrictBool | StrictInt | StrictStr | list[StrictStr] = Field(
        description="Respuesta original proporcionada por el usuario.",
    )
