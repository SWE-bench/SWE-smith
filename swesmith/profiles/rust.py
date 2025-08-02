from dataclasses import dataclass, field

from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class RustProfile(RepoProfile):
    """
    Profile for Rust repositories.
    """

    test_cmd: str = "cargo test --verbose"

    def log_parser(self, log: str):
        test_status_map = {}
        for line in log.splitlines():
            line = line.removeprefix("test ")
            if "... ok" in line:
                test_name = line.rsplit(" ... ", 1)[0].strip()
                test_status_map[test_name] = TestStatus.PASSED.value
            elif "... FAILED" in line:
                test_name = line.rsplit(" ... ", 1)[0].strip()
                test_status_map[test_name] = TestStatus.FAILED.value
        return test_status_map

    @property
    def dockerfile(self):
        return f"""FROM rust:1.88
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN {self.test_cmd}
"""


@dataclass
class Anyhow1d7ef1db(RustProfile):
    owner: str = "dtolnay"
    repo: str = "anyhow"
    commit: str = "1d7ef1db5414ac155ad6254685673c90ea4c7d77"


@dataclass
class Base64cac5ff84c(RustProfile):
    owner: str = "marshallpierce"
    repo: str = "rust-base64"
    commit: str = "cac5ff84cd771b1a9f52da020b053b35f0ff3ede"


@dataclass
class Clap3716f9f4(RustProfile):
    owner: str = "clap-rs"
    repo: str = "clap"
    commit: str = "3716f9f4289594b43abec42b2538efd1a90ff897"
    test_cmd: str = "make test-full ARGS=--verbose"


@dataclass
class Hyperc88df788(RustProfile):
    owner: str = "hyperium"
    repo: str = "hyper"
    commit: str = "c88df7886c74a1ade69c0b4c68eaf570c8111622"
    test_cmd: str = "cargo test --verbose --features full"


@dataclass
class Itertools041c733c(RustProfile):
    owner: str = "rust-itertools"
    repo: str = "itertools"
    commit: str = "041c733cb6fbfe6aae5cce28766dc6020043a7f9"
    test_cmd: str = "cargo test --verbose --all-features"


@dataclass
class Jsoncd55b5a0(RustProfile):
    owner: str = "serde-rs"
    repo: str = "json"
    commit: str = "cd55b5a0ff5f88f1aeb7a77c1befc9ddb3205201"


@dataclass
class Log3aa1359e(RustProfile):
    owner: str = "rust-lang"
    repo: str = "log"
    commit: str = "3aa1359e926a39f841791207d6e57e00da3e68e2"


@dataclass
class Semver37bcbe69(RustProfile):
    owner: str = "dtolnay"
    repo: str = "semver"
    commit: str = "37bcbe69d9259e4770643b63104798f7cc5d653c"


@dataclass
class Tokioab3ff69c(RustProfile):
    owner: str = "tokio-rs"
    repo: str = "tokio"
    commit: str = "ab3ff69cf2258a8c696b2dca89a2cef4ff114c1c"
    test_cmd: str = "cargo test --verbose --features full -- --skip try_exists"
    timeout: int = 180
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )


@dataclass
class Uuid2fd9b614(RustProfile):
    owner: str = "uuid-rs"
    repo: str = "uuid"
    commit: str = "2fd9b614c92e4e4b18928e2f539d82accf8eaeee"
    test_cmd: str = "cargo test --verbose --all-features"


# Register all Rust profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, RustProfile)
        and obj.__name__ != "RustProfile"
    ):
        registry.register_profile(obj)
