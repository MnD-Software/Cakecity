from collections.abc import AsyncIterator
import httpx


class WooCommerceClient:
    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str):
        if not all((base_url, consumer_key, consumer_secret)):
            raise ValueError("WooCommerce URL and API credentials are required")
        self.base_url = base_url.rstrip("/")
        self.auth = (consumer_key, consumer_secret)

    async def product_pages(self, *, per_page: int = 50) -> AsyncIterator[list[dict]]:
        page = 1
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), auth=self.auth) as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/wp-json/wc/v3/products",
                    params={"page": page, "per_page": per_page, "orderby": "id", "order": "asc"},
                )
                response.raise_for_status()
                products = response.json()
                if not products:
                    return
                yield products
                if page >= int(response.headers.get("X-WP-TotalPages", page)):
                    return
                page += 1

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), auth=self.auth) as client:
            response = await client.request(method, f"{self.base_url}/wp-json/wc/v3/{path.lstrip('/')}", **kwargs)
            response.raise_for_status()
            return response.json()

    async def find_order_by_reference(self, reference: str) -> dict | None:
        candidates = await self._request("GET", "orders", params={
            "search": reference, "status": "any", "per_page": 20,
        })
        for order in candidates:
            metadata = {item.get("key"): item.get("value") for item in order.get("meta_data", [])}
            if metadata.get("_cakecity_reference") == reference:
                return order
        return None

    async def create_paid_order(self, payload: dict) -> dict:
        existing = await self.find_order_by_reference(payload["reference"])
        if existing:
            return existing
        return await self._request("POST", "orders", json=payload["order"])

    async def update_order_stage(self, woo_id: int, stage: str) -> dict:
        status = "completed" if stage == "delivered" else "processing"
        return await self._request("PUT", f"orders/{woo_id}", json={
            "status": status,
            "meta_data": [{"key": "_cakecity_stage", "value": stage}],
        })
