import logging
from collections.abc import Sequence
from uuid import UUID

import httpx

from app.rag.contracts import EvidenceError, ManifestPoint

logger = logging.getLogger(__name__)


class QdrantAdapter:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.client = http_client

    async def ensure_collection(self, collection_name: str, dimensions: int, distance: str) -> None:
        """Create the collection if it doesn't exist."""
        # Qdrant distances: Cosine, Dot, Euclid
        qdrant_distance = "Cosine" if distance == "cosine" else "Dot" if distance == "dot" else "Euclid"
        
        try:
            resp = await self.client.get(f"/collections/{collection_name}")
            if resp.status_code == 200:
                return  # Exists
            elif resp.status_code == 404:
                # Create it
                payload = {
                    "vectors": {
                        "size": dimensions,
                        "distance": qdrant_distance
                    }
                }
                create_resp = await self.client.put(f"/collections/{collection_name}", json=payload)
                create_resp.raise_for_status()
            else:
                resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.exception("Qdrant ensure_collection failed")
            raise EvidenceError("QDRANT_COMMUNICATION_ERROR") from e

    async def upsert_points(
        self, collection_name: str, points: list[dict]
    ) -> None:
        """Upsert points to Qdrant. points should be a list of Qdrant point objects:
        {'id': uuid_str, 'vector': [float], 'payload': {}}
        """
        if not points:
            return

        payload = {"points": points}
        try:
            # wait=true ensures we wait for Qdrant to process before returning
            resp = await self.client.put(f"/collections/{collection_name}/points?wait=true", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.exception("Qdrant upsert_points failed")
            raise EvidenceError("QDRANT_COMMUNICATION_ERROR") from e

    async def fetch_manifest(
        self, collection_name: str, generation_id: UUID, expected_count: int
    ) -> list[ManifestPoint]:
        """Scrolls Qdrant to retrieve point IDs and chunk_hashes for a specific generation.
        Returns a list of ManifestPoint.
        """
        points = []
        offset = None
        limit = 100
        
        try:
            while True:
                payload = {
                    "filter": {
                        "must": [
                            {
                                "key": "generation_id",
                                "match": {"value": str(generation_id)}
                            }
                        ]
                    },
                    "limit": limit,
                    "with_payload": True,
                    "with_vector": False
                }
                if offset:
                    payload["offset"] = offset

                resp = await self.client.post(
                    f"/collections/{collection_name}/points/scroll", json=payload
                )
                resp.raise_for_status()
                data = resp.json()["result"]
                
                for item in data.get("points", []):
                    pt_id = UUID(item["id"])
                    payload_data = item.get("payload", {})
                    chunk_hash = payload_data.get("chunk_hash")
                    if chunk_hash:
                        points.append(ManifestPoint(point_id=pt_id, chunk_hash=chunk_hash))
                
                offset = data.get("next_page_offset")
                if not offset:
                    break
                    
            return points
        except httpx.HTTPError as e:
            logger.exception("Qdrant fetch_manifest failed")
            raise EvidenceError("QDRANT_COMMUNICATION_ERROR") from e

    async def search(
        self, collection_name: str, query_vector: Sequence[float], limit: int = 5, generation_id: UUID | None = None
    ) -> list[tuple[UUID, float]]:
        """Search Qdrant for nearest points."""
        payload: dict = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": False,
            "with_vector": False,
        }
        if generation_id:
            payload["filter"] = {
                "must": [
                    {
                        "key": "generation_id",
                        "match": {"value": str(generation_id)}
                    }
                ]
            }
        
        try:
            resp = await self.client.post(f"/collections/{collection_name}/points/search", json=payload)
            resp.raise_for_status()
            data = resp.json()["result"]
            return [(UUID(item["id"]), float(item["score"])) for item in data]
        except httpx.HTTPError as e:
            logger.exception("Qdrant search failed")
            raise EvidenceError("QDRANT_COMMUNICATION_ERROR") from e
