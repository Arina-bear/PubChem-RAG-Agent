import base64
from urllib.parse import quote

import anyio
import pubchempy as pcp

from app.config import Settings
from app.errors.models import AppError, ErrorCode
from app.services.cache import TTLCache
from app.transport.pubchem import PubChemTransport


class PubChemAdapter:
    def __init__(self, settings: Settings, transport: PubChemTransport, cache: TTLCache) -> None:
        self.settings = settings
        self.transport = transport
        self.cache = cache

    async def resolve_cids(self, input_mode: str, identifier: str, *, limit: int) -> list[int]:
        if input_mode == "cid":
            try:
                return [int(identifier)]
            except ValueError as exc:
                raise AppError(
                    ErrorCode.VALIDATION_ERROR,
                    "CID должен быть целым числом.",
                    http_status=400,
                ) from exc

        cache_key = f"resolve:{input_mode}:{identifier.lower()}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return list(cached)[:limit]  # type: ignore[arg-type]

        cids = await self._resolve_with_pubchempy(input_mode, identifier)
        if not cids:
            cids = await self._resolve_direct(input_mode, identifier, limit=limit)
        if not cids:
            raise AppError(
                ErrorCode.NO_MATCH,
                "PubChem не нашёл совпадений для указанного идентификатора.",
                http_status=404,
            )

        deduplicated = list(dict.fromkeys(int(cid) for cid in cids))
        await self.cache.set(cache_key, deduplicated, ttl_seconds=1800)
        return deduplicated[:limit]

    async def _resolve_with_pubchempy(self, input_mode: str, identifier: str) -> list[int]:
        if input_mode not in {"name", "smiles", "inchikey"}:
            return []

        def call_pubchempy() -> list[int]:
            return list(pcp.get_cids(identifier, namespace=input_mode))

        try:
            return await anyio.to_thread.run_sync(call_pubchempy)
        except Exception:
            return []

    async def _resolve_direct(self, input_mode: str, identifier: str, *, limit: int) -> list[int]:
        if input_mode == "formula":
            payload = await self.transport.request_json(
                f"/compound/fastformula/{quote(identifier, safe='')}/cids/JSON",
                params={"MaxRecords": limit},
            )
            return payload.get("IdentifierList", {}).get("CID", [])

        if input_mode not in {"name", "smiles", "inchikey"}:
            raise AppError(
                ErrorCode.UNSUPPORTED_QUERY,
                f"Режим ввода '{input_mode}' не поддерживается в текущей версии.",
                http_status=400,
            )

        encoded_identifier = quote(identifier, safe="")
        payload = await self.transport.request_json(f"/compound/{input_mode}/{encoded_identifier}/cids/JSON")
        return payload.get("IdentifierList", {}).get("CID", [])

    async def fetch_compound_snapshot(
        self,
        cid: int,
        *,
        include_synonyms: bool = True,
        include_image: bool = True,
    ) -> dict:
        properties = await self._fetch_properties(cid)
        synonyms = await self._fetch_synonyms(cid) if include_synonyms else None
        image_data_url = await self._fetch_image_data_url(cid) if include_image else None
        return {
            "cid": cid,
            "properties": properties,
            "synonyms": synonyms,
            "image_data_url": image_data_url,
        }

    async def fetch_description(self, cid: int) -> dict:
        cache_key = f"description:{cid}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        payload = await self.transport.request_json(f"/compound/cid/{cid}/description/JSON")
        await self.cache.set(cache_key, payload, ttl_seconds=86400)
        return payload

    async def fetch_xrefs(self, cid: int) -> dict:
        cache_key = f"xrefs:{cid}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        payload = await self.transport.request_json(
            f"/compound/cid/{cid}/xrefs/PubMedID,PatentID,SourceName/JSON"
        )
        await self.cache.set(cache_key, payload, ttl_seconds=86400)
        return payload

    async def _fetch_properties(self, cid: int) -> dict:
        cache_key = f"properties:{cid}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        property_names = ",".join(
            [
                "Title",
                "IUPACName",
                "MolecularFormula",
                "MolecularWeight",
                "ExactMass",
                "XLogP",
                "TPSA",
                "CanonicalSMILES",
                "ConnectivitySMILES",
                "SMILES",
                "InChIKey",
            ]
        )
        payload = await self.transport.request_json(f"/compound/cid/{cid}/property/{property_names}/JSON")
        await self.cache.set(cache_key, payload, ttl_seconds=86400)
        return payload

    async def _fetch_synonyms(self, cid: int) -> dict:
        cache_key = f"synonyms:{cid}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        payload = await self.transport.request_json(f"/compound/cid/{cid}/synonyms/JSON")
        await self.cache.set(cache_key, payload, ttl_seconds=86400)
        return payload

    async def _fetch_image_data_url(self, cid: int) -> str:
        cache_key = f"image:{cid}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        png_bytes = await self.transport.request_bytes(
            f"/compound/cid/{cid}/PNG",
            params={"image_size": "small"},
            accept="image/png",
        )
        data_url = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"
        await self.cache.set(cache_key, data_url, ttl_seconds=86400)
        return data_url
