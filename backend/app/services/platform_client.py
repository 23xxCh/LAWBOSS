"""
电商平台 API 对接层

抽象基类 + 具体实现，支持：
- Amazon SP-API (Selling Partner API)
- Shopee Open API
- Lazada Open API
- eBay REST API

每个平台实现：
- fetch_listings(): 拉取产品 Listing
- update_listing(): 更新 Listing 内容
- get_categories(): 获取平台类别映射
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class PlatformListing:
    """平台 Listing 数据模型"""
    listing_id: str
    platform: str          # amazon, shopee, lazada, ebay
    title: str             # 产品标题
    description: str       # 产品描述
    category: str          # 平台类别
    market: str            # 目标市场 (EU, US, SEA_SG, SEA_TH, SEA_MY)
    sku: Optional[str] = None
    asin: Optional[str] = None  # Amazon ASIN
    item_id: Optional[str] = None  # Shopee/Lazada item_id
    price: Optional[float] = None
    currency: Optional[str] = None
    status: str = "active"  # active, inactive, flagged
    last_checked: Optional[datetime] = None
    raw_data: Optional[Dict] = None


class BasePlatformClient(ABC):
    """电商平台客户端抽象基类"""

    @abstractmethod
    async def fetch_listings(
        self,
        market: str,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> List[PlatformListing]:
        """拉取产品 Listing 列表"""
        pass

    @abstractmethod
    async def fetch_listing_detail(self, listing_id: str) -> Optional[PlatformListing]:
        """拉取单个 Listing 详情"""
        pass

    @abstractmethod
    async def update_listing_description(self, listing_id: str, new_description: str) -> bool:
        """更新 Listing 描述（合规版本回写）"""
        pass

    @abstractmethod
    def map_category(self, platform_category: str) -> str:
        """将平台类别映射为 CrossGuard 内部类别"""
        pass


class AmazonClient(BasePlatformClient):
    """Amazon SP-API 客户端

    需要配置环境变量：
    - AMAZON_SELLER_ID
    - AMAZON_ACCESS_TOKEN (LWA Token)
    - AMAZON_REFRESH_TOKEN
    - AMAZON_CLIENT_ID
    - AMAZON_CLIENT_SECRET
    """

    # Amazon 类别 → CrossGuard 类别映射
    CATEGORY_MAP = {
        "Beauty": "化妆品",
        "Health & Personal Care": "化妆品",
        "Skin Care": "化妆品",
        "Hair Care": "化妆品",
        "Cosmetics": "化妆品",
        "Electronics": "电子产品",
        "Grocery & Gourmet Food": "食品",
        "Health Care": "膳食补充剂",
        "Vitamins & Dietary Supplements": "膳食补充剂",
        "Toys & Games": "玩具",
        "Clothing": "纺织品",
    }

    def __init__(self):
        self.seller_id = os.getenv("AMAZON_SELLER_ID", "")
        self.access_token = os.getenv("AMAZON_ACCESS_TOKEN", "")
        self.refresh_token = os.getenv("AMAZON_REFRESH_TOKEN", "")
        self.client_id = os.getenv("AMAZON_CLIENT_ID", "")
        self.client_secret = os.getenv("AMAZON_CLIENT_SECRET", "")
        self.enabled = bool(self.seller_id and self.refresh_token)

    async def fetch_listings(
        self,
        market: str,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> List[PlatformListing]:
        """通过 SP-API 拉取 Catalog Items"""
        if not self.enabled:
            logger.warning("Amazon SP-API 未配置")
            return []

        try:
            import httpx
            # SP-API endpoint 根据市场不同
            endpoints = {
                "US": "https://sellingpartnerapi-na.amazon.com",
                "EU": "https://sellingpartnerapi-eu.amazon.com",
                "SEA_SG": "https://sellingpartnerapi-fe.amazon.com",
                "SEA_TH": "https://sellingpartnerapi-fe.amazon.com",
                "SEA_MY": "https://sellingpartnerapi-fe.amazon.com",
            }
            base_url = endpoints.get(market, endpoints["US"])

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "x-amz-access-token": self.access_token,
                "Host": base_url.replace("https://", ""),
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{base_url}/catalog/2022-04-01/items",
                    headers=headers,
                    params={
                        "sellerId": self.seller_id,
                        "marketplaceIds": self._get_marketplace_id(market),
                        "pageSize": limit,
                    },
                )

                if resp.status_code == 200:
                    return self._parse_catalog_items(resp.json(), market)
                else:
                    logger.error(f"Amazon SP-API 错误: {resp.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Amazon 拉取失败: {e}")
            return []

    async def fetch_listing_detail(self, listing_id: str) -> Optional[PlatformListing]:
        """拉取单个 Listing 详情"""
        # 实际实现需要调用 SP-API 的 GET /catalog/2022-04-01/items/{asin}
        logger.info(f"拉取 Amazon Listing: {listing_id}")
        return None

    async def update_listing_description(self, listing_id: str, new_description: str) -> bool:
        """通过 SP-API 更新 Listing 描述"""
        # 实际实现需要调用 PUT /listings/2021-08-01/items/{sellerId}/{sku}
        logger.info(f"更新 Amazon Listing {listing_id} 描述")
        return False

    def map_category(self, platform_category: str) -> str:
        return self.CATEGORY_MAP.get(platform_category, platform_category)

    def _get_marketplace_id(self, market: str) -> str:
        """获取 Amazon Marketplace ID"""
        ids = {
            "US": "ATVPDKIKX0DER",
            "EU": "A1PA6795UKMFR9",  # DE
            "SEA_SG": "A19VAU5N5RQ3L0",
            "SEA_TH": "A2CNAOELMNGQO1",
            "SEA_MY": "A2VIG5Z9UE0J2E",
        }
        return ids.get(market, ids["US"])

    def _parse_catalog_items(self, data: dict, market: str) -> List[PlatformListing]:
        """解析 SP-API Catalog Items 响应"""
        listings = []
        for item in data.get("items", []):
            listings.append(PlatformListing(
                listing_id=item.get("asin", ""),
                platform="amazon",
                title=item.get("summaries", [{}])[0].get("itemName", ""),
                description=item.get("summaries", [{}])[0].get("itemDescription", ""),
                category=self.map_category(item.get("summaries", [{}])[0].get("productType", "")),
                market=market,
                asin=item.get("asin"),
                status="active",
                raw_data=item,
            ))
        return listings


class ShopeeClient(BasePlatformClient):
    """Shopee Open API 客户端

    需要配置环境变量：
    - SHOPEE_PARTNER_ID
    - SHOPEE_PARTNER_KEY
    - SHOPEE_SHOP_ID
    - SHOPEE_ACCESS_TOKEN
    """

    CATEGORY_MAP = {
        "Health & Beauty": "化妆品",
        "Skin Care": "化妆品",
        "Mobile & Gadgets": "电子产品",
        "Food & Beverages": "食品",
        "Health": "膳食补充剂",
    }

    def __init__(self):
        self.partner_id = os.getenv("SHOPEE_PARTNER_ID", "")
        self.partner_key = os.getenv("SHOPEE_PARTNER_KEY", "")
        self.shop_id = os.getenv("SHOPEE_SHOP_ID", "")
        self.access_token = os.getenv("SHOPEE_ACCESS_TOKEN", "")
        self.enabled = bool(self.partner_id and self.shop_id and self.access_token)

    async def fetch_listings(
        self,
        market: str,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> List[PlatformListing]:
        if not self.enabled:
            logger.warning("Shopee API 未配置")
            return []

        try:
            import httpx
            base_urls = {
                "SEA_SG": "https://partner.shopeemobile.com.sg",
                "SEA_TH": "https://partner.shopeemobile.co.th",
                "SEA_MY": "https://partner.shopeemobile.com.my",
            }
            base_url = base_urls.get(market, base_urls["SEA_SG"])

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{base_url}/api/v2/product/get_item_list",
                    params={
                        "partner_id": self.partner_id,
                        "shop_id": self.shop_id,
                        "access_token": self.access_token,
                        "offset": 0,
                        "page_size": limit,
                    },
                )
                if resp.status_code == 200:
                    return self._parse_items(resp.json(), market)
                return []
        except Exception as e:
            logger.error(f"Shopee 拉取失败: {e}")
            return []

    async def fetch_listing_detail(self, listing_id: str) -> Optional[PlatformListing]:
        return None

    async def update_listing_description(self, listing_id: str, new_description: str) -> bool:
        return False

    def map_category(self, platform_category: str) -> str:
        return self.CATEGORY_MAP.get(platform_category, platform_category)

    def _parse_items(self, data: dict, market: str) -> List[PlatformListing]:
        listings = []
        for item in data.get("response", {}).get("item_list", []):
            listings.append(PlatformListing(
                listing_id=str(item.get("item_id", "")),
                platform="shopee",
                title=item.get("item_name", ""),
                description="",  # Shopee 需要额外调用获取详情
                category=self.map_category(item.get("category_name", "")),
                market=market,
                item_id=str(item.get("item_id")),
                status="active" if item.get("item_status") == "NORMAL" else "inactive",
            ))
        return listings


# ===== 平台客户端工厂 =====

def get_platform_client(platform: str) -> Optional[BasePlatformClient]:
    """获取平台客户端实例"""
    clients = {
        "amazon": AmazonClient,
        "shopee": ShopeeClient,
    }
    cls = clients.get(platform)
    if cls:
        client = cls()
        return client if client.enabled else None
    return None


def get_available_platforms() -> List[Dict[str, str]]:
    """获取已配置的可用平台"""
    platforms = []
    for name, cls in [("amazon", AmazonClient), ("shopee", ShopeeClient)]:
        client = cls()
        if client.enabled:
            platforms.append({"platform": name, "status": "connected"})
        else:
            platforms.append({"platform": name, "status": "not_configured"})
    return platforms
