from dataclasses import dataclass, field

from swesmith.constants import ENV_NAME
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class RustProfile(RepoProfile):
    """
    Profile for Rust repositories.
    """

    test_cmd: str = "cargo test --verbose"
    exts: list[str] = field(default_factory=lambda: [".rs"])
    rust_version: str = "1.88"

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
        return f"""FROM rust:{self.rust_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN {self.test_cmd} || true
"""


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

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
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

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN cargo build --release
"""


@dataclass
class RustClippyf4f579f4(RustProfile):
    owner: str = "rust-lang"
    repo: str = "rust-clippy"
    commit: str = "f4f579f4ac455b76ddadc85553ba19b115dd144e"


@dataclass
class Hexyl2e264378(RustProfile):
    owner: str = "sharkdp"
    repo: str = "hexyl"
    commit: str = "2e2643782d6ced9b5ac75596169a79127d8e535a"


@dataclass
class Oha8dc63499(RustProfile):
    owner: str = "hatoo"
    repo: str = "oha"
    commit: str = "8dc63499f84b3116652987dac711eca687ccc2fd"


@dataclass
class Indicatifdbd26eb18(RustProfile):
    owner: str = "console-rs"
    repo: str = "indicatif"
    commit: str = "dbd26eb18157e5fad18c79e1933ad5f249165d6c"


@dataclass
class Melodyf4af9b48(RustProfile):
    owner: str = "yoav-lavi"
    repo: str = "melody"
    commit: str = "f4af9b4829555fedb687eb5f6f5755ce3c5ef738"


@dataclass
class RustOwl655bc5c3(RustProfile):
    owner: str = "cordx56"
    repo: str = "rust-owl"
    commit: str = "655bc5c37e59156954fa9af3e6466602e7dfa814"


@dataclass
class Quinnbb359ccd(RustProfile):
    owner: str = "quinn-rs"
    repo: str = "quinn"
    commit: str = "bb359ccd7dfbc18b472bcb61e6800be6dc886264"


@dataclass
class Shellharden6a6ffd42(RustProfile):
    owner: str = "anordal"
    repo: str = "shellharden"
    commit: str = "6a6ffd42f6a9d8b558d479346d09233ae5e7a2ae"


@dataclass
class Grexfa3e8ed7(RustProfile):
    owner: str = "pemistahl"
    repo: str = "grex"
    commit: str = "fa3e8ed71c43ea92f9f0e43ab31e1c82d006d5dd"


@dataclass
class Htmlq6e31bc81(RustProfile):
    owner: str = "mgdm"
    repo: str = "htmlq"
    commit: str = "6e31bc814332b2521f0316d0ed9bf0a1c521b6e6"


@dataclass
class Xh4a6e44fc(RustProfile):
    owner: str = "ducaale"
    repo: str = "xh"
    commit: str = "4a6e44fcb562126959c54ca33b673cf7d707a63e"


@dataclass
class Lightningcss400f705e(RustProfile):
    owner: str = "parcel-bundler"
    repo: str = "lightningcss"
    commit: str = "400f705e63e139c326f480aed11e1416f5a3a61f"


@dataclass
class Miniserve8449e8b1(RustProfile):
    owner: str = "svenstaro"
    repo: str = "miniserve"
    commit: str = "8449e8b118ffd61de8df970b56b0796f891e3697"


@dataclass
class Tailpsin6278437c(RustProfile):
    owner: str = "bensadeh"
    repo: str = "tailpsin"
    commit: str = "6278437c3d28f2e95201f3b0c8a471b8668eed5b"


@dataclass
class SccacheCd7dcd5f(RustProfile):
    owner: str = "mozilla"
    repo: str = "sccache"
    commit: str = "cd7dcd5f73b7c77b826ad5173b6af6642ad03a3e"


@dataclass
class Boa14e5c634(RustProfile):
    owner: str = "boa-dev"
    repo: str = "boa"
    commit: str = "14e5c6342d72ef128ecad92f66f4c54641bd9561"


@dataclass
class Pastelb60e8993(RustProfile):
    owner: str = "sharkdp"
    repo: str = "pastel"
    commit: str = "b60e89932629b2d162e1ff9f3976a5a0ef1e5db9"


@dataclass
class Anyhow2c0bda4c(RustProfile):
    owner: str = "dtolnay"
    repo: str = "anyhow"
    commit: str = "2c0bda4ce944d943e7141f0316b0ea996602238e"


@dataclass
class Cxx0d80b351(RustProfile):
    owner: str = "dtolnay"
    repo: str = "cxx"
    commit: str = "0d80b351886a00af9a7120369f22a0b7f0affd72"


@dataclass
class Rustfmt86261bfb(RustProfile):
    owner: str = "rust-lang"
    repo: str = "rustfmt"
    commit: str = "86261bfb87a207030b1dfeef0f832ac13f369b1a"


@dataclass
class TealdeerC5d62e59(RustProfile):
    owner: str = "tealdeer-rs"
    repo: str = "tealdeer"
    commit: str = "c5d62e5987b38705814b72354373c50fe165dbb3"


@dataclass
class Image26edc698(RustProfile):
    owner: str = "image-rs"
    repo: str = "image"
    commit: str = "26edc698463cc2a0e7b9735ca41d375dce0449a2"


@dataclass
class Duacli8570c154(RustProfile):
    owner: str = "Byron"
    repo: str = "dua-cli"
    commit: str = "8570c1543e3cd0983725f6e1938bf3e73442678a"


@dataclass
class Serenityc6219206(RustProfile):
    owner: str = "serenity-rs"
    repo: str = "serenity"
    commit: str = "c6219206a38161a9e8d78660f19b44ba4dfb4ed9"


@dataclass
class Tideb32f680d(RustProfile):
    owner: str = "http-rs"
    repo: str = "tide"
    commit: str = "b32f680d5bd14bc2ce7c81bef9ce99859028b20f"


@dataclass
class Rhai6b132e55(RustProfile):
    owner: str = "rhaiscript"
    repo: str = "rhai"
    commit: str = "6b132e55167e6fc82a2348e90d507141e1204a12"


@dataclass
class Rayon5b4eb339(RustProfile):
    owner: str = "rayon-rs"
    repo: str = "rayon"
    commit: str = "5b4eb339c06943cbb71d8368e78343c049e6d71c"


@dataclass
class Brootd6c798ed(RustProfile):
    owner: str = "Canop"
    repo: str = "broot"
    commit: str = "d6c798edbd136dbe5b67566ad74a7daa97e8ae49"


@dataclass
class OneFetchE5958cec(RustProfile):
    owner: str = "o2sh"
    repo: str = "onefetch"
    commit: str = "e5958cec1e5d17d72405f1c96cf30ae1e2defa16"


@dataclass
class Reqwest01f03a4c(RustProfile):
    owner: str = "seanmonstar"
    repo: str = "reqwest"
    commit: str = "01f03a4c01fb13e2262a513ed21e2b84b5186f46"


@dataclass
class Dust62bf1e14(RustProfile):
    owner: str = "bootandy"
    repo: str = "dust"
    commit: str = "62bf1e14de73b14bdf5c691be29e6dcc4de352aa"


@dataclass
class Bore8e059cda(RustProfile):
    owner: str = "ekzhang"
    repo: str = "bore"
    commit: str = "8e059cdaf993d25d92080a2b28a71949a4545d03"


@dataclass
class Warp3449d3d9(RustProfile):
    owner: str = "seanmonstar"
    repo: str = "warp"
    commit: str = "3449d3d9816ea3898059e62b5325716c1cc27c8b"


@dataclass
class Gping26eb5b91(RustProfile):
    owner: str = "orf"
    repo: str = "gping"
    commit: str = "26eb5b914b1d90d75ebf23c3a9ae8ee3ebd6f217"


@dataclass
class TokenizersEcad3f18(RustProfile):
    owner: str = "huggingface"
    repo: str = "tokenizers"
    commit: str = "ecad3f18a3e340635f5393cfb22cf70d3502f64a"
    test_cmd: str = f"cd ~/{ENV_NAME}/tokenizers && cargo test --verbose"

    @property
    def dockerfile(self):
        return f"""FROM rust:{self.rust_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN {self.test_cmd} || true
"""


# Register all Rust profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, RustProfile)
        and obj.__name__ != "RustProfile"
    ):
        registry.register_profile(obj)
