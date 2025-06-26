import re
from dataclasses import dataclass

from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class GoProfile(RepoProfile):
    """
    Profile for Golang repositories.

    This class provides Golang-specific defaults and functionality for
    repository profiles.
    """

    test_cmd: str = "go test -v ./..."

    def log_parser(self, log: str) -> dict[str, str]:
        """Parser for test logs generated with 'go test'"""
        test_status_map = {}

        # Pattern to match test result lines
        pattern = r"^--- (PASS|FAIL|SKIP): (.+) \((.+)\)$"

        for line in log.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                status, test_name, _ = match.groups()
                if status == "PASS":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif status == "FAIL":
                    test_status_map[test_name] = TestStatus.FAILED.value
                elif status == "SKIP":
                    test_status_map[test_name] = TestStatus.SKIPPED.value

        return test_status_map


@dataclass
class Gin3c12d2a8(GoProfile):
    owner: str = "gin-gonic"
    repo: str = "gin"
    commit: str = "3c12d2a80e40930632fc4a4a4e1a45140f33fb12"

    @property
    def dockerfile(self):
        return f"""FROM golang:1.24
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN go mod tidy
RUN go test ./...
"""


# Register all Go profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, GoProfile)
        and obj.__name__ != "GoProfile"
    ):
        global_registry.register_profile(obj)
