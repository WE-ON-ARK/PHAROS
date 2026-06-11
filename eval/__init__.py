"""PHAROS evaluation package: experiment runner, statistical analysis, reporting."""

from eval.report import build_report
from eval.runner import ConditionResult, ExperimentResult, run_experiment
from eval.stats import HypothesisResults, HypothesisTest, analyse

__all__ = [
    "ConditionResult",
    "ExperimentResult",
    "HypothesisResults",
    "HypothesisTest",
    "analyse",
    "build_report",
    "run_experiment",
]
