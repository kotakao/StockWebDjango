"""Database Router 路由測試（不需資料庫）。"""

from django.contrib.contenttypes.models import ContentType

from apps.market.models import DailyQuote, MarketDaily
from config.routers import MarketRouter

router = MarketRouter()


def test_market_models_read_from_market_db():
    """market app 模型讀取路由至 market 庫。"""
    assert router.db_for_read(DailyQuote) == "market"
    assert router.db_for_read(MarketDaily) == "market"


def test_market_models_have_no_write_target():
    """market app 模型寫入路由為 None（封鎖寫入）。"""
    assert router.db_for_write(DailyQuote) is None
    assert router.db_for_write(MarketDaily) is None


def test_non_market_models_use_default():
    """非 market app 模型不被本 router 接管（回 None → 交預設）。"""
    assert router.db_for_read(ContentType) is None
    assert router.db_for_write(ContentType) is None


def test_allow_migrate_blocks_market():
    """market app 不 migrate；任何 app 皆不得 migrate 進 market 庫。"""
    assert router.allow_migrate("market", "market") is False
    assert router.allow_migrate("default", "market") is False
    assert router.allow_migrate("market", "core") is False
    # 非 market app 於 default 庫不受本 router 限制
    assert router.allow_migrate("default", "core") is None
