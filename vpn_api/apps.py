from django.apps import AppConfig


class VpnApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vpn_api'

    def ready(self):
        import vpn_api.signals  # noq