#!/usr/bin/env python
"""Django 管理指令進入點。"""
import os
import sys


def main() -> None:
    """設定預設 settings 模組並執行 Django 管理指令。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - 環境未安裝 Django 時的提示
        raise ImportError(
            "無法匯入 Django，請確認已安裝並啟用虛擬環境。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
