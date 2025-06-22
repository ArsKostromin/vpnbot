from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'
    verbose_name = 'Пользователи'
    
    def ready(self):
        # Импортируем сигналы только после полной загрузки Django
        try:
            import user.signals  # noqa
        except ImportError:
            pass