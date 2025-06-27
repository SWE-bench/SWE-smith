from dataclasses import dataclass

from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class RustProfile(RepoProfile):
    """
    Profile for Rust repositories.
    """

    test_cmd: str = "cargo test --verbose"

    def log_parser(self, log: str):
        test_status_map = {}
        for line in log.split("\n"):
            if "... ok" in line:
                test_name = line.rsplit(" ... ", 1)[0].strip()
                test_status_map[test_name] = TestStatus.PASSED.value
            elif "... FAILED" in line:
                test_name = line.rsplit(" ... ", 1)[0].strip()
                test_status_map[test_name] = TestStatus.FAILED.value
        return test_status_map


@dataclass
class Jsoncd55b5a0(RustProfile):
    owner: str = "serde-rs"
    repo: str = "json"
    commit: str = "cd55b5a0ff5f88f1aeb7a77c1befc9ddb3205201"

    @property
    def dockerfile(self):
        return f"""FROM rust:1.88
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN cargo test --verbose
"""


# Register all Rust profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, RustProfile)
        and obj.__name__ != "RustProfile"
    ):
        global_registry.register_profile(obj)
