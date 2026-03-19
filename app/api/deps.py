from fastapi import Request

from app.services.cleaning_service import CleaningService


def get_cleaning_service(request: Request) -> CleaningService:
    # Instância única criada no `main.py`, guardada em `app.state`.
    return request.app.state.cleaning_service

