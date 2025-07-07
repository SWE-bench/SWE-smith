from pathlib import Path
from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    FAIL_TO_FAIL,
    FAIL_TO_PASS,
    KEY_PREDICTION,
    PASS_TO_FAIL,
    PASS_TO_PASS,
    TESTS_TIMEOUT,
    ResolvedStatus,
    TestStatus,
)
from swebench.harness.grading import get_resolution_status
from swesmith.constants import (
    TEST_OUTPUT_END,
    TEST_OUTPUT_START,
)
from swesmith.profiles import global_registry


def read_test_output(filename: str):
    content = Path(filename).read_text()
    if APPLY_PATCH_FAIL in content:
        return None, False
    if TESTS_TIMEOUT in content:
        return None, False
    if TEST_OUTPUT_START not in content or TEST_OUTPUT_END not in content:
        return content, False
    start_sep = f"+ : '{TEST_OUTPUT_START}'"
    end_sep = f"+ : '{TEST_OUTPUT_END}'"
    start_idx = content.find(start_sep)
    end_idx = content.find(end_sep)
    if start_idx > end_idx:
        raise ValueError(
            "Invalid test output - Start and end markers are not in correct order"
        )
    return content[start_idx:end_idx][len(start_sep) :], True


def get_valid_report(
    val_pregold_path: str,
    val_postgold_path: str,
    instance: dict,
) -> dict[str, list[str]]:
    """
    Get a report of changes in test pass/fail status between pre-gold and post-gold validation logs

    Args:
        val_pregold_path (str): path to pre-gold validation log
        val_postgold_path (str): path to post-gold validation log
    Returns:
        report (dict): map of type of status change to list of test cases
    """
    rp = global_registry.get(instance["repo"])

    val_pregold_output, found_pregold = read_test_output(val_pregold_path)
    val_postgold_output, found_postgold = read_test_output(val_postgold_path)
    pregold_sm = rp.log_parser(val_pregold_output) if found_pregold else {}
    postgold_sm = rp.log_parser(val_postgold_output) if found_postgold else {}

    report = {
        FAIL_TO_PASS: [],
        PASS_TO_PASS: [],
        FAIL_TO_FAIL: [],
        PASS_TO_FAIL: [],
    }

    for test_case in postgold_sm:
        if test_case not in pregold_sm:
            continue
        elif (
            pregold_sm[test_case] == TestStatus.PASSED.value
            and postgold_sm[test_case] == TestStatus.PASSED.value
        ):
            report[PASS_TO_PASS].append(test_case)
        elif (
            pregold_sm[test_case] == TestStatus.FAILED.value
            and postgold_sm[test_case] == TestStatus.PASSED.value
        ):
            report[FAIL_TO_PASS].append(test_case)
        elif (
            pregold_sm[test_case] == TestStatus.FAILED.value
            and postgold_sm[test_case] == TestStatus.FAILED.value
        ):
            report[FAIL_TO_FAIL].append(test_case)
        elif (
            pregold_sm[test_case] == TestStatus.PASSED.value
            and postgold_sm[test_case] == TestStatus.FAILED.value
        ):
            report[PASS_TO_FAIL].append(test_case)

    return report


def test_passed(case: str, sm: dict[str, str]) -> bool:
    return case in sm and sm[case] in [
        TestStatus.PASSED.value,
        TestStatus.XFAIL.value,
    ]


def test_failed(case: str, sm: dict[str, str]) -> bool:
    return case not in sm or sm[case] in [
        TestStatus.FAILED.value,
        TestStatus.ERROR.value,
    ]


def get_eval_tests_report(
    eval_status_map: dict[str, str],
    gold_results: dict[str, str],
    calculate_to_fail: bool = False,
) -> dict[str, dict[str, list[str]]]:
    """
    Create a report based on failure/pass change from gold results to eval results.

    Args:
        eval_sm (dict): evaluation status map
        gold_results (dict): gold results
        calculate_to_fail (bool): whether to calculate metrics for "x to fail" tests
    Returns:
        report (dict): report of metrics

    Metric Definitions (Gold Result Pair + Eval Result):
    - Fail-Pass (F2P) + P: Success (Resolution)
    - Pass-Pass (P2P) + P: Success (Maintenance)
    - Fail-Pass (F2P) + F: Failure
    - Pass-Pass (P2P) + F: Failure

    Miscellaneous Definitions
    - Fail-Fail (F2F) + F: Failure Maintenance
    - Pass-Fail (P2F) + F: Not considered
    - Fail-Fail (F2F) + P: Success (Extra Credit)
    - Pass-Fail (P2F) + P: Not considered
    """
    # Calculate resolution metrics
    f2p_success = []
    f2p_failure = []
    for test_case in gold_results[FAIL_TO_PASS]:
        if test_passed(test_case, eval_status_map):
            f2p_success.append(test_case)
        elif test_failed(test_case, eval_status_map):
            f2p_failure.append(test_case)

    # Calculate maintenance metrics
    p2p_success = []
    p2p_failure = []
    for test_case in gold_results[PASS_TO_PASS]:
        if test_passed(test_case, eval_status_map):
            p2p_success.append(test_case)
        elif test_failed(test_case, eval_status_map):
            p2p_failure.append(test_case)

    results = {
        FAIL_TO_PASS: {
            "success": f2p_success,
            "failure": f2p_failure,
        },
        PASS_TO_PASS: {
            "success": p2p_success,
            "failure": p2p_failure,
        },
    }

    f2f_success = []
    f2f_failure = []
    p2f_success = []
    p2f_failure = []
    if calculate_to_fail:
        # Calculate "extra credit" metrics
        for test_case in gold_results[FAIL_TO_FAIL]:
            if test_passed(test_case, eval_status_map):
                f2f_success.append(test_case)
            elif test_failed(test_case, eval_status_map):
                f2f_failure.append(test_case)
        # Calculate not considered metrics
        for test_case in gold_results[PASS_TO_FAIL]:
            if test_passed(test_case, eval_status_map):
                p2f_success.append(test_case)
            elif test_failed(test_case, eval_status_map):
                p2f_failure.append(test_case)

    results.update(
        {
            FAIL_TO_FAIL: {
                "success": f2f_success,
                "failure": f2f_failure,
            },
            PASS_TO_FAIL: {
                "success": p2f_success,
                "failure": p2f_failure,
            },
        }
    )
    return results


def get_eval_report(
    prediction: dict,
    inst: dict,
    test_log_path: str,
    f2p_only: bool = False,
):
    report_map = {
        "patch_exists": False,
        "resolved": False,
    }
    rp = global_registry.get_from_inst(inst)

    # Check if model patch exists
    if prediction[KEY_PREDICTION] is None:
        return report_map
    report_map["patch_exists"] = True

    # Get evaluation logs
    test_output, found = read_test_output(test_log_path)
    if not found:
        return report_map
    test_status_map = rp.log_parser(test_output)

    if f2p_only:
        # Only examine f2p tests
        test_files = rp._get_f2p_test_files(inst)
        filter_irrelevant_tests = (
            lambda tests: [
                x for x in tests if any([x.startswith(y) for y in test_files])
            ]
            if len(test_files) > 0
            else tests
        )
        inst[FAIL_TO_PASS] = filter_irrelevant_tests
        inst[PASS_TO_PASS] = filter_irrelevant_tests

    # Get evaluation test report
    report = get_eval_tests_report(test_status_map, inst)
    if get_resolution_status(report) == ResolvedStatus.FULL.value:
        report_map["resolved"] = True
    report_map["tests_status"] = report

    return report_map
