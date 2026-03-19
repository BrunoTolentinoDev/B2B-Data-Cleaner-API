import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.cache import InMemoryCache
from app.services.cleaning_service import AIResponseError, CleaningService


def _fake_openai_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


class FakeDeepSeekClient:
    def __init__(self, contents: list[str]) -> None:
        self._contents = contents
        self.calls = 0

        async def create(*_args, **_kwargs):
            self.calls += 1
            idx = min(self.calls - 1, len(self._contents) - 1)
            return _fake_openai_response(self._contents[idx])

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


@pytest.mark.asyncio
async def test_enrich_lead_parses_json_from_markdown_and_coerces_fields():
    settings = Settings()
    cache = InMemoryCache(ttl_seconds=60)
    service = CleaningService(settings=settings, cache=cache)

    content = (
        "```json\n"
        "{"
        "\"nome_padronizado\":\"Bruno Tolentino\","
        "\"setor_estimado\":\"Tecnologia\","
        "\"perfil_vendas\":\"empresa vende software e consultoria\","
        "\"sales_hook\":\"Chame Bruno Tolentino e aumente conversões com propostas sob medida\","
        "\"is_garbage\":\"false\""
        "}\n"
        "```"
    )
    service._client = FakeDeepSeekClient([content])

    result = await service.enrich_lead(" bruno  tolEN   me ")
    assert result["nome_padronizado"] == "Bruno Tolentino"
    assert result["setor_estimado"] == "Tecnologia"
    assert isinstance(result["perfil_vendas"], str)
    assert len(result["perfil_vendas"].split()) <= 10
    assert result["sales_hook"]
    assert result["sales_hook"][-1] in ".!?"
    assert result["is_garbage"] is False


@pytest.mark.asyncio
async def test_enrich_lead_raises_if_required_fields_missing():
    settings = Settings()
    cache = InMemoryCache(ttl_seconds=60)
    service = CleaningService(settings=settings, cache=cache)

    content = '{"nome_padronizado":"X"}'
    service._client = FakeDeepSeekClient([content])

    with pytest.raises(AIResponseError):
        await service.enrich_lead("teste")


@pytest.mark.asyncio
async def test_enrich_lead_uses_cache_and_singleflight():
    settings = Settings()
    cache = InMemoryCache(ttl_seconds=60)
    service = CleaningService(settings=settings, cache=cache)

    content = (
        "{"
        "\"nome_padronizado\":\"Ada Lovelace\","
        "\"setor_estimado\":\"Tecnologia\","
        "\"perfil_vendas\":\"empresa de tecnologia\","
        "\"sales_hook\":\"Descubra como Ada Lovelace pode gerar valor rápido\","
        "\"is_garbage\":false"
        "}"
    )
    fake = FakeDeepSeekClient([content])
    service._client = fake

    results = await asyncio.gather(*[service.enrich_lead("ada lovelace") for _ in range(8)])
    assert all(r["nome_padronizado"] == "Ada Lovelace" for r in results)
    assert all(r["sales_hook"][-1] in ".!?" for r in results)
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_sales_hook_drops_incomplete_trailing_clause():
    settings = Settings()
    cache = InMemoryCache(ttl_seconds=60)
    service = CleaningService(settings=settings, cache=cache)

    content = (
        "{"
        "\"nome_padronizado\":\"Magazine Luiza\","
        "\"setor_estimado\":\"Varejo\","
        "\"perfil_vendas\":\"varejo nacional\","
        "\"sales_hook\":\"Magazine Luiza, líder no varejo brasileiro, pode otimizar suas operações com nossas\","
        "\"is_garbage\":false"
        "}"
    )
    service._client = FakeDeepSeekClient([content])
    result = await service.enrich_lead("magazine luiza")
    assert "com nossas" not in result["sales_hook"]
    assert result["sales_hook"][-1] in ".!?"

