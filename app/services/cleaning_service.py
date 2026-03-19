import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings
from app.services.cache import InMemoryCache


class AIResponseError(RuntimeError):
    pass


class CleaningService:
    def __init__(self, settings: Settings, cache: InMemoryCache) -> None:
        self.settings = settings
        self.cache = cache

        # openai já suporta base_url customizado.
        self._client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

    def _normalize_name_key(self, raw_name: str) -> str:
        # Mantém chave estável para cache: diferença apenas de case/espacos.
        normalized = re.sub(r"\s+", " ", (raw_name or "").strip()).lower()
        return normalized

    def _extract_json_object(self, text: str) -> dict[str, Any]:
        if not text:
            raise AIResponseError("Empty AI response.")

        cleaned = text.strip()
        cleaned = re.sub(r"```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("```", "").strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIResponseError("AI response does not contain a JSON object.")

        obj_text = cleaned[start : end + 1]
        try:
            parsed = json.loads(obj_text)
        except json.JSONDecodeError as e:
            raise AIResponseError("AI response contains invalid JSON.") from e

        if not isinstance(parsed, dict):
            raise AIResponseError("AI JSON root must be an object.")
        return parsed

    def _collapse_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _limit_words(self, text: str, max_words: int) -> str:
        words = [w for w in self._collapse_spaces(text).split() if w]
        if not words:
            return ""
        return " ".join(words[:max_words])

    def _finalize_sales_hook(self, text: str) -> str:
        """
        Parágrafo único (espaços normais). Remove cauda óbvia cortada no meio
        (ex.: termina em vírgula ou última oração incompleta) e garante ponto final.
        """
        s = self._collapse_spaces(text.replace("\n", " ").replace("\r", " "))
        if not s:
            return ""

        if re.search(r'[.!?]["\']?\s*$', s):
            return s

        if "," in s:
            head, _, tail = s.rpartition(", ")
            tail_stripped = tail.rstrip(",").strip()
            incomplete_tail = (
                tail_stripped
                and not re.search(r"[.!?]$", tail_stripped)
                and (
                    len(tail_stripped.split()) <= 8
                    or re.search(
                        r"\b(com|com as|com os|com nossas|com nossos|das|dos|nas|nos|para um|para os|no seu|na sua)\s*$",
                        tail_stripped,
                        re.I,
                    )
                )
            )
            if incomplete_tail and head.strip():
                s = head.rstrip(",").strip()

        s = s.rstrip(",;:")
        if not re.search(r'[.!?]["\']?\s*$', s):
            s += "."
        return s

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"true", "1", "yes"}:
                return True
            if v in {"false", "0", "no"}:
                return False
        raise AIResponseError("AI returned invalid boolean for 'is_garbage'.")

    async def enrich_lead(self, raw_name: str) -> dict[str, Any]:
        raw_name = (raw_name or "").strip()
        if not raw_name:
            raise ValueError("Nome inválido.")

        cache_key = self.cache.make_key("lead_enrichment", self._normalize_name_key(raw_name))

        async def compute() -> dict[str, Any]:
            prompt = (
                "Enriqueça um lead B2B SOMENTE pelo NOME. "
                "Responda com UM único objeto JSON válido, sem markdown, sem texto fora do JSON.\n"
                "Chaves: \"nome_padronizado\", \"setor_estimado\", \"perfil_vendas\", \"sales_hook\", \"is_garbage\".\n"
                "Regras:\n"
                "- nome_padronizado: iniciais maiúsculas, sem espaços duplicados.\n"
                "- setor_estimado: um único setor curto (ex: Varejo, Tecnologia).\n"
                "- perfil_vendas: no máximo 10 palavras, sem ponto final.\n"
                "- sales_hook: um PARÁGRAFO para o vendedor (2 a 5 frases COMPLETAS), em português, "
                "citando o nome_padronizado; cada frase deve fazer sentido sozinha; "
                "NÃO termine no meio de uma ideia, NÃO termine em vírgula ou preposição solta; "
                "o último caractere deve ser . ! ou ?\n"
                "- is_garbage: true/false; true se for lixo (ex: asdfgh, teste genérico, não interessa).\n"
                f"Nome bruto: {raw_name}"
            )

            resp = await self._client.chat.completions.create(
                model=self.settings.DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Você enriquece leads B2B. JSON válido; sales_hook sempre parágrafo completo.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=1024,
            )

            content = (resp.choices[0].message.content or "").strip()
            data = self._extract_json_object(content)

            required = {"nome_padronizado", "setor_estimado", "perfil_vendas", "sales_hook", "is_garbage"}
            if not required.issubset(set(data.keys())):
                raise AIResponseError("AI response missing required fields.")

            nome_padronizado = self._collapse_spaces(str(data["nome_padronizado"]))
            if not nome_padronizado:
                raise AIResponseError("AI returned empty 'nome_padronizado'.")

            perfil_vendas = self._limit_words(str(data["perfil_vendas"]), 10)
            raw_hook = str(data["sales_hook"])
            if len(raw_hook) > 2000:
                raise AIResponseError("sales_hook exceeds max length.")
            sales_hook = self._finalize_sales_hook(raw_hook)
            if not sales_hook:
                raise AIResponseError("AI returned empty 'sales_hook'.")
            is_garbage = self._coerce_bool(data["is_garbage"])

            return {
                "nome_padronizado": nome_padronizado,
                "setor_estimado": self._collapse_spaces(str(data["setor_estimado"])),
                "perfil_vendas": perfil_vendas,
                "sales_hook": sales_hook,
                "is_garbage": is_garbage,
            }

        return await self.cache.get_or_compute(cache_key, compute)

