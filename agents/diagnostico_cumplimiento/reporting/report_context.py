from pydantic import BaseModel, ConfigDict


class CompanyReportInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = None

    worker_count: int

    risk_class: str

    norm: str

    requirements_article: int