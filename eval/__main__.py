"""Entry point: python -m eval — run experiment, analyse, print report."""

from eval.report import build_report
from eval.runner import run_experiment
from eval.stats import analyse


def main() -> None:
    """Run the full 2×2 experiment pipeline and print the markdown report."""
    result = run_experiment()
    hyp = analyse(result)
    print(build_report(result, hyp))


if __name__ == "__main__":
    main()
