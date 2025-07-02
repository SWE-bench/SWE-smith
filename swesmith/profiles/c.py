import re

from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class CProfile(RepoProfile):
    """
    Profile for C repositories.
    """


@dataclass
class Jqb9e19de76(CProfile):
    owner: str = "jqlang"
    repo: str = "jq"
    commit: str = "b9e19de76e6e19d044007ead65d164710dc98877"
    test_cmd: str = "make check"

    @property
    def dockerfile(self):
        return f"""FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NONINTERACTIVE_SEEN=true \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8
ENV TZ=Etc/UTC
RUN apt-get update \
    && apt-get install -y build-essential autoconf libtool git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN autoreconf -i \
    && ./configure \
    --disable-docs \
    --with-oniguruma=builtin \
    --enable-static \
    --enable-all-static \
    --prefix=/usr/local
RUN make clean
RUN touch src/parser.y src/lexer.l
RUN make -j$(nproc)
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        pattern = r"^\s*(PASS|FAIL):\s(.+)$"
        for line in log.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                status, test_name = match.groups()
                if status == "PASS":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif status == "FAIL":
                    test_status_map[test_name] = TestStatus.FAILED.value
        return test_status_map


@dataclass
class Valkeyfc7c04e4(CProfile):
    owner: str = "valkey-io"
    repo: str = "valkey"
    commit: str = "fc7c04e4f8ba86dfbac1ec059db457fb44ed0a2d"
    test_cmd: str = "TERM=dumb ./runtest --durable"

    @property
    def dockerfile(self):
        return f"""FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN sed -i 's/^# deb-src/deb-src/' /etc/apt/sources.list
RUN apt update && \
    apt install -y pkg-config wget git build-essential libtool automake autoconf tcl bison flex cmake python3 python3-pip python3-venv python-is-python3 && \
    rm -rf /var/lib/apt/lists/*
RUN adduser --disabled-password --gecos 'dog' nonroot
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN cd deps/jemalloc && ./autogen.sh
RUN make distclean
RUN make
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        pattern = r"^\[(ok|err|skip|ignore)\]:\s(.+?)(?:\s\((\d+\s*m?s)\))?$"
        for line in log.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                status, test_name, _duration = match.groups()
                if status == "ok":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif status == "err":
                    # Strip out file path information from failed test names
                    test_name = re.sub(r"\s+in\s+\S+$", "", test_name)
                    test_status_map[test_name] = TestStatus.FAILED.value
                elif status == "skip" or status == "ignore":
                    test_status_map[test_name] = TestStatus.SKIPPED.value
        return test_status_map


# Register all C profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, CProfile)
        and obj.__name__ != "CProfile"
    ):
        global_registry.register_profile(obj)
