"""
Legacy HTML formatter (read-only archive).

New Sage UI routes should not import this module for runtime logic.
Use ``status_diagnosis_builder`` / ``recommendation_diagnosis_builder`` instead.
Legacy HTML formatters remain here for non-Sage fallback paths only.
"""
from src.services.html_formatter import *  # noqa: F401,F403
