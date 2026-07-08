"""Routing truth table + median/agreement aggregation. No network, no env vars."""

import pytest

from app.models import JudgeSample
from app.steps.grade_projects import aggregate, route

S3 = {"impact_innovation": 3, "execution_quality": 3, "presentation_clarity": 3}
S5 = {"impact_innovation": 3, "execution_quality": 5, "presentation_clarity": 3}


@pytest.mark.parametrize(
    "confidence,scores,off_topic,agreement,expected",
    [
        (0.9, S3, False, False, False),
        (0.69, S3, False, False, True),
        (0.7, S3, False, False, False),
        (0.9, S5, False, False, True),
        (0.9, S3, True, False, True),
        (0.9, S3, False, True, True),
        (0.5, S5, True, True, True),
    ],
)
def test_routing_truth_table(confidence, scores, off_topic, agreement, expected):
    assert route(confidence, scores, off_topic, agreement) is expected


def _sample(i, e, p, confidence=0.8, off_topic=False):
    return JudgeSample(
        scores={"impact_innovation": i, "execution_quality": e, "presentation_clarity": p},
        confidence=confidence,
        off_topic=off_topic,
    )


def test_aggregate_median_and_confidence():
    samples = [_sample(3, 4, 3, 0.9), _sample(4, 4, 3, 0.8), _sample(3, 4, 4, 0.7)]
    scores, confidence, off_topic, agreement = aggregate(samples)
    assert scores == {"impact_innovation": 3, "execution_quality": 4, "presentation_clarity": 3}
    assert confidence == 0.8
    assert off_topic is False
    assert agreement is False


def test_aggregate_flags_disagreement_when_range_exceeds_one():
    samples = [_sample(2, 3, 3), _sample(4, 3, 3), _sample(3, 3, 3)]
    _, _, _, agreement = aggregate(samples)
    assert agreement is True


def test_aggregate_off_topic_majority():
    samples = [
        _sample(3, 3, 3, off_topic=True),
        _sample(3, 3, 3, off_topic=True),
        _sample(3, 3, 3, off_topic=False),
    ]
    _, _, off_topic, _ = aggregate(samples)
    assert off_topic is True
