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

    test_cmd: str = "go test -v -count=1 ./..."

    @property
    def dockerfile(self):
        return f"""FROM golang:1.24
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN go mod tidy
"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parser for test logs generated with 'go test'"""
        test_status_map = {}

        pattern_status_map = [
            (re.compile(r"--- PASS: (\S+)"), TestStatus.PASSED.value),
            (re.compile(r"--- FAIL: (\S+)"), TestStatus.FAILED.value),
            (re.compile(r"FAIL:?\s?(.+?)\s"), TestStatus.FAILED.value),
            (re.compile(r"--- SKIP: (\S+)"), TestStatus.SKIPPED.value),
        ]
        for line in log.split("\n"):
            for pattern, status in pattern_status_map:
                match = pattern.match(line.strip())
                if match:
                    test_name = match.group(1)
                    test_status_map[test_name] = status
                    break

        return test_status_map


@dataclass
class Gin3c12d2a8(GoProfile):
    owner: str = "gin-gonic"
    repo: str = "gin"
    commit: str = "3c12d2a80e40930632fc4a4a4e1a45140f33fb12"


@dataclass
class Fzf976001e4(GoProfile):
    owner: str = "junegunn"
    repo: str = "fzf"
    commit: str = "976001e47459973b5e72565f3047cc9d9e20241d"


@dataclass
class Beego8fd113aa(GoProfile):
    owner: str = "beego"
    repo: str = "beego"
    commit: str = "8fd113aa0937a11c45eb41cbf147f33df7e9fb6f"


@dataclass
class Caddy77dd12cc(GoProfile):
    owner: str = "caddyserver"
    repo: str = "caddy"
    commit: str = "77dd12cc785990c5c5da947b4e883029ab8bd552"


@dataclass
class Cli4c47bad6(GoProfile):
    owner: str = "cli"
    repo: str = "cli"
    commit: str = "4c47bad604d8b206a4bc686507b2e9a3bed2b317"


@dataclass
class Concourse24abde66(GoProfile):
    owner: str = "concourse"
    repo: str = "concourse"
    commit: str = "24abde66ec91853eebdcf273a064e31accae9f25"


@dataclass
class Etcd721ba5bc(GoProfile):
    owner: str = "etcd-io"
    repo: str = "etcd"
    commit: str = "721ba5bc2489e0588b224a099a0fa369f166b4e5"


@dataclass
class Frp61330d4d(GoProfile):
    owner: str = "fatedier"
    repo: str = "frp"
    commit: str = "61330d4d794180c38d1f8ff7e9024b7f0f69d717"


@dataclass
class Gorm1e8baf54(GoProfile):
    owner: str = "go-gorm"
    repo: str = "gorm"
    commit: str = "1e8baf545953dd58e2f301f4dfef5febbc12da0f"


@dataclass
class Hugocfc8d315(GoProfile):
    owner: str = "gohugoio"
    repo: str = "hugo"
    commit: str = "cfc8d315b4f1a21c3daed0f9e78b7edb19f298d1"


@dataclass
class Grpcaa57e6af(GoProfile):
    owner: str = "grpc"
    repo: str = "grpc-go"
    commit: str = "aa57e6af6cbc8e1285315b338b092420f014c732"


@dataclass
class Istio8c687844(GoProfile):
    owner: str = "istio"
    repo: str = "istio"
    commit: str = "8c687844a88bfc4a7d4f998e4c950cd9243334c3"


@dataclass
class Lazygit91d8c251(GoProfile):
    owner: str = "jesseduffield"
    repo: str = "lazygit"
    commit: str = "91d8c25183fde8e0d9ae51b8a24acb545b9cb278"


@dataclass
class Echo98ca08e7(GoProfile):
    owner: str = "labstack"
    repo: str = "echo"
    commit: str = "98ca08e7dd64075b858e758d6693bf9799340756"


@dataclass
class Natsserver2ee2e24c(GoProfile):
    owner: str = "nats-io"
    repo: str = "nats-server"
    commit: str = "2ee2e24cb10924adb699ecb68b89e8ce2523ea75"


@dataclass
class Addressec203a4f(GoProfile):
    owner: str = "bojanz"
    repo: str = "address"
    commit: str = "ec203a4f7f569c03a0f83e2e749b63947481fe4c"


@dataclass
class Prometheus74aca682(GoProfile):
    owner: str = "prometheus"
    repo: str = "prometheus"
    commit: str = "74aca682b77d66f5761bd68459f3b570ec34ce2d"


@dataclass
class Syncthing06dd8ee(GoProfile):
    owner: str = "syncthing"
    repo: str = "syncthing"
    commit: str = "06dd8ee6d75e14a62b7da28b2eec33f2f5695fc8"


@dataclass
class Gozero75cebb65(GoProfile):
    owner: str = "zeromicro"
    repo: str = "go-zero"
    commit: str = "75cebb65f88cc6019d9e16e34c4a567e621f4dd5"


@dataclass
class Goatcounter854b1dd2(GoProfile):
    owner: str = "arp242"
    repo: str = "goatcounter"
    commit: str = "854b1dd2408ca95645ad03ea3fd01ccfe267261a"


@dataclass
class Gotests16a93f6e(GoProfile):
    owner: str = "cweill"
    repo: str = "gotests"
    commit: str = "16a93f6eb6519118b1d282e2f233596a98dd7e96"


# Register all Go profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, GoProfile)
        and obj.__name__ != "GoProfile"
    ):
        global_registry.register_profile(obj)
