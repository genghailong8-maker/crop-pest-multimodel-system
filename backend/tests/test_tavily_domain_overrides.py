from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

from app import config
from app.search.tavily import TavilySearchProvider


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"query": "test", "results": []}


class _AsyncClient:
    def __init__(self, **_: object) -> None:
        self.payload: dict[str, object] | None = None

    async def __aenter__(self) -> _AsyncClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, *_: object, **kwargs: object) -> _Response:
        self.payload = kwargs["json"]  # type: ignore[assignment]
        return _Response()


class TavilyDomainOverrideTests(unittest.IsolatedAsyncioTestCase):
    async def payload_for(self, class_name: str) -> dict[str, object]:
        client = _AsyncClient()
        settings = replace(config.settings, tavily_api_key="unit-test-only")
        with (
            patch.object(config, "settings", settings),
            patch("app.search.tavily.httpx.AsyncClient", return_value=client),
        ):
            await TavilySearchProvider().search_evidence(class_name, "harms")
        assert client.payload is not None
        return client.payload

    async def test_tungro_search_is_restricted_to_irri(self) -> None:
        payload = await self.payload_for("水稻东格鲁病毒病")
        self.assertEqual(payload["include_domains"], ["knowledgebank.irri.org"])
        self.assertEqual(payload["include_domains_mode"], "restrict")
        self.assertNotIn("site:", str(payload["query"]))

    async def test_other_disease_searches_keep_existing_domain_behavior(self) -> None:
        payload = await self.payload_for("玉米灰斑病")
        self.assertNotIn("include_domains", payload)
        self.assertNotIn("include_domains_mode", payload)


if __name__ == "__main__":
    unittest.main()
