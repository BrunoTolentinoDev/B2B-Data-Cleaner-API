from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_cleaning_service
from app.schemas.lead import LeadValidateRequest, LeadValidateResponse
from app.services.cleaning_service import CleaningService
from app.services.validators import (
    is_valid_cnpj,
    is_valid_email,
    normalize_cnpj,
    normalize_email,
)

router = APIRouter(prefix="/validate", tags=["lead"])


@router.post("/lead", response_model=LeadValidateResponse)
async def validate_lead(
    payload: LeadValidateRequest,
    cleaning_service: CleaningService = Depends(get_cleaning_service),
) -> LeadValidateResponse:
    email = normalize_email(payload.email)
    if not is_valid_email(email):
        raise HTTPException(status_code=422, detail="E-mail inválido.")

    if not is_valid_cnpj(payload.cnpj):
        raise HTTPException(status_code=422, detail="CNPJ inválido.")

    nome_raw = payload.nome.strip()
    if not nome_raw:
        raise HTTPException(status_code=422, detail="Nome inválido.")

    enriched = await cleaning_service.enrich_lead(nome_raw)

    return LeadValidateResponse(
        nome_padronizado=enriched["nome_padronizado"],
        setor_estimado=enriched["setor_estimado"],
        perfil_vendas=enriched["perfil_vendas"],
        sales_hook=enriched["sales_hook"],
        is_garbage=enriched["is_garbage"],
        email=email,
        cnpj=normalize_cnpj(payload.cnpj),
    )

