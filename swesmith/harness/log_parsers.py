import re

from swebench.harness.constants import TestStatus


def parse_log_pytest(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with PyTest framework

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        for status in TestStatus:
            is_match = re.match(rf"^(\S+)(\s+){status.value}", line)
            if is_match:
                test_status_map[is_match.group(1)] = status.value
                continue
    return test_status_map


def parse_log_gotest(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with 'go test'

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    # Pattern to match test result lines
    pattern = r"^--- (PASS|FAIL|SKIP): (.+) \((.+)\)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name, _duration = match.groups()
            if status == "PASS":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "FAIL":
                test_status_map[test_name] = TestStatus.FAILED.value
            elif status == "SKIP":
                test_status_map[test_name] = TestStatus.SKIPPED.value

    return test_status_map


def parse_log_mypy(log: str) -> dict[str, str]:
    """Parser for test logs generated by mypy"""
    test_status_map = {}
    for line in log.split("\n"):
        for status in [
            TestStatus.PASSED.value,
            TestStatus.FAILED.value,
        ]:
            if status in line:
                test_case = line.split()[-1]
                test_status_map[test_case] = status
                break
    return test_status_map


def parse_log_python_slugify(log: str) -> dict[str, str]:
    """Parser for test logs generated by un33k/python-slugify"""
    test_status_map = {}
    pattern = r"^([a-zA-Z0-9_\-,\.\s\(\)']+)\s\.{3}\s"
    for line in log.split("\n"):
        is_match = re.match(f"{pattern}ok$", line)
        if is_match:
            test_status_map[is_match.group(1)] = TestStatus.PASSED.value
            continue
        for keyword, status in {
            "FAIL": TestStatus.FAILED,
            "ERROR": TestStatus.ERROR,
        }.items():
            is_match = re.match(f"{pattern}{keyword}$", line)
            if is_match:
                test_status_map[is_match.group(1)] = status.value
                continue
    return test_status_map


def parse_log_tornado(log: str) -> dict[str, str]:
    """Parser for test logs generated by tornadoweb/tornado"""
    test_status_map = {}
    for line in log.split("\n"):
        if line.endswith("... ok"):
            test_case = line.split(" ... ")[0]
            test_status_map[test_case] = TestStatus.PASSED.value
        elif " ... skipped " in line:
            test_case = line.split(" ... ")[0]
            test_status_map[test_case] = TestStatus.SKIPPED.value
        elif any([line.startswith(x) for x in ["ERROR:", "FAIL:"]]):
            test_case = " ".join(line.split()[1:3])
            test_status_map[test_case] = TestStatus.FAILED.value
    return test_status_map


def parse_log_paramiko(log: str) -> dict[str, str]:
    """Parser for test logs generated by paramiko/paramiko"""
    test_status_map = {}
    for line in log.split("\n"):
        for status in TestStatus:
            is_match = re.match(rf"^{status.value}\s(\S+)", line)
            if is_match:
                test_status_map[is_match.group(1)] = status.value
                continue
    return test_status_map


def parse_log_autograd(log: str) -> dict[str, str]:
    """Parser for test logs generated by pytorch/pytorch"""
    test_status_map = {}
    for line in log.split("\n"):
        for status in TestStatus:
            is_match = re.match(rf"^\[gw\d\]\s{status.value}\s(\S+)", line)
            if is_match:
                test_status_map[is_match.group(1)] = status.value
                continue
    return test_status_map


MAP_REPO_TO_PARSER = {
    "gin-gonic/gin": parse_log_gotest,
    "HIPS/autograd": parse_log_autograd,
    "paramiko/paramiko": parse_log_paramiko,
    "python/mypy": parse_log_mypy,
    "tornadoweb/tornado": parse_log_tornado,
    "un33k/python-slugify": parse_log_python_slugify,
}
