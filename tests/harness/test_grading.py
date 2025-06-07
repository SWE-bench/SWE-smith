import json

from swebench.harness.constants import (
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTION,
)
from swesmith.constants import KEY_IMAGE_NAME
from swesmith.harness.grading import (
    get_eval_report,
    get_valid_report,
    read_test_output,
)


def test_read_test_output(logs_run_evaluation):
    instance_id = "pandas-dev__pandas.95280573.pr_53652"
    test_output_path = logs_run_evaluation / instance_id / "test_output.txt"
    test_output, found = read_test_output(test_output_path)
    assert found, "Test output should be found"
    expected = """\n+ pytest --disable-warnings --color=no --tb=no --verbose pandas/tests/indexing/test_datetime.py
[1/1] Generating write_version_file with a custom command
+ /opt/miniconda3/envs/testbed/bin/ninja
============================= test session starts ==============================
platform linux -- Python 3.10.16, pytest-8.3.5, pluggy-1.5.0 -- /opt/miniconda3/envs/testbed/bin/python
cachedir: .pytest_cache
hypothesis profile 'ci' -> deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors], database=DirectoryBasedExampleDatabase(PosixPath('/testbed/.hypothesis/examples'))
rootdir: /testbed
configfile: pyproject.toml
plugins: anyio-4.8.0, xdist-3.6.1, localserver-0.9.0.post0, cython-0.3.1, hypothesis-6.127.7, cov-6.0.0
collecting ... collected 11 items

pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_get_loc_naive_dti_aware_str_deprecated PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_indexing_with_datetime_tz PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_indexing_fast_xs PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_consistency_with_tz_aware_scalar PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_indexing_with_datetimeindex_tz[setitem] PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_indexing_with_datetimeindex_tz[loc] PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_nanosecond_getitem_setitem_with_tz PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_getitem_str_slice_millisecond_resolution[DataFrame] PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_getitem_str_slice_millisecond_resolution[Series] PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_getitem_pyarrow_index[DataFrame] PASSED
pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_getitem_pyarrow_index[Series] PASSED

------------------ generated xml file: /testbed/test-data.xml ------------------
============================= slowest 30 durations =============================
0.01s call     pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_indexing_fast_xs
0.01s call     pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_getitem_pyarrow_index[DataFrame]
0.01s call     pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_nanosecond_getitem_setitem_with_tz
0.01s call     pandas/tests/indexing/test_datetime.py::TestDatetimeIndex::test_indexing_with_datetimeindex_tz[loc]

(26 durations < 0.005s hidden.  Use -vv to show these durations.)
============================== 11 passed in 0.10s ==============================\n"""
    assert test_output == expected


def test_get_eval_tests(task_instance_path, logs_run_evaluation):
    instance_id = "pandas-dev__pandas.95280573.pr_53652"
    task_instance = json.load(open(task_instance_path))
    expected = json.load(open(logs_run_evaluation / instance_id / "report.json"))
    del expected[KEY_MODEL]
    mock_prediction = {
        KEY_INSTANCE_ID: instance_id,
        KEY_PREDICTION: "example_patch",
    }
    report_map = get_eval_report(
        mock_prediction,
        task_instance,
        logs_run_evaluation / instance_id / "test_output.txt",
    )
    assert report_map == expected


def test_get_valid_report(logs_run_validation):
    report = get_valid_report(
        logs_run_validation / "test_output.txt",
        logs_run_validation / "test_output_pre_gold.txt",
        {KEY_IMAGE_NAME: "swesmith.x86_64.pandas-dev__pandas.95280573"},
    )
    assert report == json.load(open(logs_run_validation / "report.json"))
