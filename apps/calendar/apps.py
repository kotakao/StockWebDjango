"""calendar app（D7）：行事曆頁（月曆檢視除權息與法說會日期）。"""

from django.apps import AppConfig


class CalendarConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.calendar"
