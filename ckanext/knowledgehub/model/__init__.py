# -*- coding: utf-8 -*-
"""This package contains knowledgehub's data models
"""

from ckanext.knowledgehub.model.analytical_framework import (AnalyticalFramework,
                                                           af_db_setup)


__all__ = (
    'AnalyticalFramework',
    'af_db_setup'
)