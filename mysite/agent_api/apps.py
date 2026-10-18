from django.apps import AppConfig


class AgentApiConfig(AppConfig):
    """API tokens: circle admins mint per-circle tokens for MCP clients and other agents."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mysite.agent_api"
    verbose_name = "Agent API"

    def ready(self):
        from . import signals  # noqa: F401
