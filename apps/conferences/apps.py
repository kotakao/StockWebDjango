"""conferences app（D6）：法說會資訊頁（唯讀呈現 investor_conferences）。"""

from django.apps import AppConfig


class ConferencesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.conferences"
