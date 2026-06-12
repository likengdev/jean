from django.apps import AppConfig

class ImpotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'impots'

    def ready(self):
        import impots.models