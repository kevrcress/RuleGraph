"""Unit tests for feedback_service FEEDBACK_WEIGHTS config."""
import pytest
from app.services.feedback_service import FEEDBACK_WEIGHTS


class TestFeedbackWeights:

    def test_weights_dict_exists(self):
        assert isinstance(FEEDBACK_WEIGHTS, dict)

    def test_explicit_signals_present(self):
        required = {"thumbs_up", "thumbs_down", "this_is_wrong", "mark_as_verified"}
        assert required.issubset(FEEDBACK_WEIGHTS.keys())

    def test_implicit_signals_present(self):
        required = {"clicked_through", "clicked_source_doc", "searched_again_immediately",
                    "edited_rule_after_view", "conflict_resolved"}
        assert required.issubset(FEEDBACK_WEIGHTS.keys())

    def test_automated_signals_present(self):
        required = {"drift_caught_and_resolved", "coverage_gap_fixed"}
        assert required.issubset(FEEDBACK_WEIGHTS.keys())

    def test_all_weights_are_floats_in_range(self):
        for key, w in FEEDBACK_WEIGHTS.items():
            assert isinstance(w, float), f"{key} weight is not a float"
            assert 0.0 <= w <= 1.0, f"{key} weight {w} out of [0, 1] range"

    def test_positive_signals_have_higher_weight_than_negative(self):
        assert FEEDBACK_WEIGHTS["thumbs_up"] > FEEDBACK_WEIGHTS["thumbs_down"]
        assert FEEDBACK_WEIGHTS["mark_as_verified"] > FEEDBACK_WEIGHTS["this_is_wrong"]

    def test_mark_as_verified_is_max_weight(self):
        assert FEEDBACK_WEIGHTS["mark_as_verified"] == 1.0

    def test_this_is_wrong_is_minimum_weight(self):
        min_weight = min(FEEDBACK_WEIGHTS.values())
        assert FEEDBACK_WEIGHTS["this_is_wrong"] == min_weight
