from django.apps import AppConfig


class VpnApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vpn_api'

    def ready(self):
        from django.contrib import admin
        from django_celery_beat.models import (
            PeriodicTask, IntervalSchedule, CrontabSchedule,
            SolarSchedule, ClockedSchedule
        )

        for model in [PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule]:
            try:
                admin.site.unregister(model)
            except admin.sites.NotRegistered:
                pass
