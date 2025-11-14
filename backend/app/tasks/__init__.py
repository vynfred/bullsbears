#!TASKS /usr/bin/env python3
"""
BullsBears Tasks

"""

from .generate_charts import generate_charts
from .publish_to_firebase import publish_to_firebase
from .fmp_delta_update import fmp_delta_update
from .statistics_tasks import (
    update_statistics_cache,
    update_badge_data_cache,
    validate_statistics_accuracy,
    generate_statistics_report
)

__all__ = [
    "generate_charts",
    "publish_to_firebase",
    "fmp_delta_update",
    "update_statistics_cache",
    "update_badge_data_cache",
    "validate_statistics_accuracy",
    "generate_statistics_report",
]