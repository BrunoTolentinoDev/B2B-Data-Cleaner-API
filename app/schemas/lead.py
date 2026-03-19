from pydantic import BaseModel, ConfigDict, Field


class LeadValidateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    cnpj: str = Field(min_length=11, max_length=18)

    model_config = ConfigDict(extra="forbid")


class LeadValidateResponse(BaseModel):
    nome_padronizado: str
    setor_estimado: str
    perfil_vendas: str
    sales_hook: str = Field(
        ...,
        description="Parágrafo persuasivo completo (várias frases), com fechamento natural; cite o nome da empresa.",
        max_length=2000,
    )
    is_garbage: bool
    email: str
    cnpj: str

    model_config = ConfigDict(extra="forbid")

