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
RUN {self.test_cmd} || true
"""


@dataclass
class Anyhow1d7ef1db(RustProfile):
    owner: str = "dtolnay"
    repo: str = "anyhow"
    commit: str = "1d7ef1db5414ac155ad6254685673c90ea4c7d77"


@dataclass
class Base64cac5ff84(RustProfile):
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


@dataclass
class MdBook37273ba8(RustProfile):
    owner: str = "rust-lang"
    repo: str = "mdBook"
    commit: str = "37273ba8e0f86771b02f3a8a4bd3b0b3d388c573"
    test_cmd: str = "cargo test --workspace --verbose"


@dataclass
class RustCSVda000888(RustProfile):
    owner: str = "BurntSushi"
    repo: str = "rust-csv"
    commit: str = "da0008884062cf222ceb9c05f006be4bb6ac38a7"


@dataclass
class Html5everb93afc94(RustProfile):
    owner: str = "servo"
    repo: str = "html5ever"
    commit: str = "b93afc9484cf5de40b422a44f9cea86ab371e3ee"

    @property
    def dockerfile(self):
        return f"""FROM rust:1.88
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git submodule update --init
"""


@dataclass
class Byteorder5a82625f(RustProfile):
    owner: str = "BurntSushi"
    repo: str = "byteorder"
    commit: str = "5a82625fae462e8ba64cec8146b24a372b4d75c6"


@dataclass
class Chronod43108cb(RustProfile):
    owner: str = "chronotope"
    repo: str = "chrono"
    commit: str = "d43108cbfc884b0864d1cf2db7719aedf4adbf23"


@dataclass
class Rpds3e7c8ae6(RustProfile):
    owner: str = "orium"
    repo: str = "rpds"
    commit: str = "3e7c8ae693cdc6e1b255c87279b6ad8aded6401d"


@dataclass
class Rayon1fd20485(RustProfile):
    owner: str = "rayon-rs"
    repo: str = "rayon"
    commit: str = "1fd20485bd0bb55541d8080a31e104c7b758cb48"


@dataclass
class Ripgrep3b7fd442(RustProfile):
    owner: str = "BurntSushi"
    repo: str = "ripgrep"
    commit: str = "3b7fd442a6f3aa73f650e763d7cbb902c03d700e"
    test_cmd: str = "cargo test --all --verbose"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

    @property
    def dockerfile(self):
        return f"""FROM rust:1.88
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN cargo build --release
"""


@dataclass
class RustClippyf4f579f4(RustProfile):
    owner: str = "rust-lang"
    repo: str = "rust-clippy"
    commit: str = "f4f579f4ac455b76ddadc85553ba19b115dd144e"


# Register all Rust profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, RustProfile)
        and obj.__name__ != "RustProfile"
    ):
        registry.register_profile(obj)
