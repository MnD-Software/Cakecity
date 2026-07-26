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
