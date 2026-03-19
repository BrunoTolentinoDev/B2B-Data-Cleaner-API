import pytest
from httpx import ASGITransport, AsyncClient


class FakeCleaningService:
    def __init__(self) -> None:
        self.calls = 0

    async def enrich_lead(self, raw_name: str) -> dict:
        self.calls += 1
        return {
            "nome_padronizado": "Bruno Tolentino",
            "setor_estimado": "Tecnologia",
            "perfil_vendas": "empresa vende software e consultoria",
            "sales_hook": "Chame Bruno Tolentino e aumente conversões com propostas sob medida",
            "is_garbage": False,
        }


@pytest.mark.asyncio
async def test_validate_lead_rejects_invalid_email(monkeypatch):
    import main

    app = main.create_app()
    app.state.cleaning_service = FakeCleaningService()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/validate/lead",
            json={"nome": "bruno tolen me", "email": "invalid-email", "cnpj": "11.444.777/0001-61"},
        )
    assert res.status_code == 422
    assert res.json()["detail"] == "E-mail inválido."


@pytest.mark.asyncio
async def test_validate_lead_rejects_invalid_cnpj(monkeypatch):
    import main

    app = main.create_app()
    app.state.cleaning_service = FakeCleaningService()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/validate/lead",
            json={"nome": "bruno tolen me", "email": "bruno@example.com", "cnpj": "00.000.000/0000-00"},
        )
    assert res.status_code == 422
    assert res.json()["detail"] == "CNPJ inválido."


@pytest.mark.asyncio
async def test_validate_lead_returns_enriched_fields(monkeypatch):
    import main

    app = main.create_app()
    fake = FakeCleaningService()
    app.state.cleaning_service = fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/validate/lead",
            json={"nome": "bruno tolen me", "email": "bruno@example.com", "cnpj": "11.444.777/0001-61"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["nome_padronizado"] == "Bruno Tolentino"
    assert "setor_estimado" in data
    assert "perfil_vendas" in data
    assert "sales_hook" in data
    assert isinstance(data["is_garbage"], bool)
    assert data["email"] == "bruno@example.com"
    assert data["cnpj"] == "11444777000161"
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_root_and_health():
    import main

    app = main.create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert "docs" in body
        assert body["docs"] == "/docs"

        h = await client.get("/health")
        assert h.status_code == 200
        assert h.json()["status"] == "ok"

