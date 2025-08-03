import re

from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class CppProfile(RepoProfile):
    """
    Profile for C++ repositories.
    """


@dataclass
class Catch29b3f508a(CppProfile):
    owner: str = "catchorg"
    repo: str = "Catch2"
    commit: str = "9b3f508a1b1579f5366cf83d19822cb395f23528"
    test_cmd: str = "cd build && ctest"

    @property
    def dockerfile(self):
        return f"""FROM gcc:12
RUN apt-get update && apt-get install -y \
    libbrotli-dev libcurl4-openssl-dev \
    clang build-essential cmake \
    python3 python3-dev python3-pip

RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN mkdir build && cd build \
    && cmake .. -DCATCH_DEVELOPMENT_BUILD=ON \
    && make all \
    && ctest"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        re_passes = [
            re.compile(r"^-- Performing Test (.+) - Success$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\s+ Passed\s+.+$", re.IGNORECASE
            ),
        ]
        re_fails = [
            re.compile(r"^-- Performing Test (.+) - Failed$", re.IGNORECASE),
            re.compile(
                r"^\d+/\d+ Test\s+#\d+: (.+) \.+\*\*\*Failed\s+.+$", re.IGNORECASE
            ),
        ]
        re_skips = [
            re.compile(r"^-- Performing Test (.+) - skipped$", re.IGNORECASE),
        ]

        for line in log.splitlines():
            line = line.strip().lower()
            if not line:
                continue

            for re_pass in re_passes:
                pass_match = re_pass.match(line)
                if pass_match:
                    test = pass_match.group(1)
                    test_status_map[test] = TestStatus.PASSED.value

            for re_fail in re_fails:
                fail_match = re_fail.match(line)
                if fail_match:
                    test = fail_match.group(1)
                    test_status_map[test] = TestStatus.FAILED.value

            for re_skip in re_skips:
                skip_match = re_skip.match(line)
                if skip_match:
                    test = skip_match.group(1)
                    test_status_map[test] = TestStatus.SKIPPED.value

        return test_status_map


# Register all C++ profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, CppProfile)
        and obj.__name__ != "CppProfile"
    ):
        registry.register_profile(obj)
