import ckan.lib.jobs as jobs
from ckanext.knowledgehub.lib.quality import (
    Accuracy,
    Completeness,
    Consistency,
    DataQualityMetrics,
    Timeliness,
    Uniqueness,
    Validity,
)


def calculate_metrics(package_id):
    metrics = DataQualityMetrics(metrics=[
        Accuracy(),
        Completeness(),
        Consistency(),
        Timeliness(),
        Uniqueness(),
        Validity()
    ])

    metrics.calculate_metrics_for_dataset(package_id)


def schedule_data_quality_check(package_id):
    jobs.enqueue(calculate_metrics, [package_id])