"""stocks 序列化（薄層）：StockSnapshot → JSON（snake_case，數值缺漏回 null）。"""

from rest_framework import serializers

from .models import StockSnapshot


class StockSnapshotSerializer(serializers.ModelSerializer):
    """個股快照序列化，排除內部 id；trade_date 以 ISO 日期輸出。"""

    class Meta:
        model = StockSnapshot
        exclude = ["id"]
