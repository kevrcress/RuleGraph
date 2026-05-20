"""Unit tests for impact_service._build_business_summary."""
import pytest
from app.services.impact_service import _build_business_summary


class TestBuildBusinessSummary:

    def test_empty_returns_no_dependencies(self):
        result = _build_business_summary([], [], [], 0)
        assert "No downstream dependencies found" in result

    def test_services_included_in_summary(self):
        services = [{"name": "PaymentsService"}, {"name": "BillingService"}]
        result = _build_business_summary(services, [], [], 0)
        assert "2 service" in result
        assert "PaymentsService" in result

    def test_related_rules_counted(self):
        rules = [{"title": "Late Fee", "status": "active"}, {"title": "Grace Period", "status": "approved"}]
        result = _build_business_summary([], rules, [], 0)
        assert "2 related" in result

    def test_subscriber_count_included(self):
        result = _build_business_summary([], [], [], 5)
        assert "5 subscriber" in result

    def test_no_file_paths_in_summary(self):
        services = [{"name": "OrderingService"}]
        result = _build_business_summary(services, [], [], 0)
        assert ".cs" not in result
        assert "/" not in result
