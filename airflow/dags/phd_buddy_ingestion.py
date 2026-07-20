"""Daily PhD Buddy paper sync, acquisition, indexing, reporting, and cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task


@dag(
    dag_id="phd_buddy_daily_ingestion",
    schedule="@daily",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    tags=["phd-buddy", "research", "ingestion"],
)
def phd_buddy_daily_ingestion():
    @task(retries=2, retry_delay=timedelta(minutes=2))
    def sync_recommendations() -> dict:
        from phd_buddy.services.ingestion import sync_recommendations as run

        return run()

    @task(retries=2, retry_delay=timedelta(minutes=2))
    def acquire_pending_papers() -> dict:
        from phd_buddy.services.ingestion import acquire_pending_papers as run

        return run()

    @task
    def index_library_papers(_: dict) -> dict:
        from phd_buddy.services.ingestion import index_library_papers as run

        return run()

    @task
    def generate_daily_report(recommendations: dict, acquisition: dict, indexing: dict) -> dict:
        from phd_buddy.services.ingestion import write_ingestion_report

        return write_ingestion_report(recommendations, acquisition, indexing)

    @task
    def clean_up(_: dict) -> dict:
        from phd_buddy.services.ingestion import cleanup_ingestion_artifacts

        return cleanup_ingestion_artifacts()

    recommendation_result = sync_recommendations()
    acquisition_result = acquire_pending_papers()
    indexing_result = index_library_papers(acquisition_result)
    report = generate_daily_report(recommendation_result, acquisition_result, indexing_result)
    clean_up(report)


phd_buddy_daily_ingestion()
