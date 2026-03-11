from celery import Celery


celery_app = Celery("extraction_engine")


def configure_celery(broker_url: str, backend_url: str) -> None:
    """Configure celery with broker/backend URLs. Called at worker startup."""
    celery_app.conf.update(
        broker_url=broker_url,
        result_backend=backend_url,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )


# Auto-configure from settings if available (deferred to avoid import-time errors)
try:
    from extraction_engine.config import get_settings

    _settings = get_settings()
    configure_celery(_settings.redis_url, _settings.redis_url)
except Exception:
    # Settings not available (e.g. during testing without .env)
    pass

celery_app.autodiscover_tasks(["extraction_engine.worker"])
