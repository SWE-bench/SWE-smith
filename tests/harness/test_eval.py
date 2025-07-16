import json
import pytest

from swesmith.harness.eval import main as run_evaluation

# Existing test


def test_run_evaluation():
    run_evaluation(
        "test_sanity",
        2,
        instance_ids=[
            "kennethreitz__records.5941ab27.combine_file__95trbjmz",
            "kurtmckee__feedparser.cad965a3.combine_file__115z1mk8",
        ],
    )


# New tests for artifacts
@pytest.mark.parametrize(
    "instance_id",
    [
        "pandas-dev__pandas.95280573.pr_53652",
        "pydantic__pydantic.acb0f10f.pr_8316",
    ],
)
def test_eval_artifacts_exist_and_valid(logs_run_evaluation, instance_id):
    inst_dir = logs_run_evaluation / instance_id
    report_path = inst_dir / "report.json"
    test_output_path = inst_dir / "test_output.txt"
    # Check files exist
    assert report_path.exists(), f"Missing report.json for {instance_id}"
    assert test_output_path.exists(), f"Missing test_output.txt for {instance_id}"
    # Check report.json is valid JSON and has required keys
    with open(report_path) as f:
        report = json.load(f)
    assert "patch_exists" in report
    assert "resolved" in report
    assert "tests_status" in report
    # Check test_output.txt is not empty
    with open(test_output_path) as f:
        content = f.read()
    assert len(content) > 0
    assert "test session starts" in content


def test_eval_summary_report(logs_run_evaluation):
    summary_path = logs_run_evaluation / "report.json"
    assert summary_path.exists(), "Missing summary report.json"
    with open(summary_path) as f:
        summary = json.load(f)
    assert "resolved" in summary
    assert "unresolved" in summary
    assert "total" in summary
    assert isinstance(summary["ids_resolved"], list)
    assert isinstance(summary["ids_unresolved"], list)
