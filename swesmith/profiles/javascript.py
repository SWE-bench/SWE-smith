import re

from dataclasses import dataclass
from swesmith.constants import KEY_PATCH
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry
from swesmith.profiles.utils import X11_DEPS
from unidiff import PatchSet


@dataclass
class JavaScriptProfile(RepoProfile):
    """
    Profile for JavaScript repositories.
    """


def parse_log_jest(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with Jest. Assumes --verbose flag.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    pattern = r"^\s*(✓|✕|○)\s(.+?)(?:\s\((\d+\s*m?s)\))?$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status_symbol, test_name, _duration = match.groups()
            if status_symbol == "✓":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status_symbol == "✕":
                test_status_map[test_name] = TestStatus.FAILED.value
            elif status_symbol == "○":
                test_status_map[test_name] = TestStatus.SKIPPED.value
    return test_status_map


def parse_log_mocha(log: str) -> dict[str, str]:
    test_status_map = {}
    pattern = r"^\s*(✔|✖|-)\s(.+?)(?:\s\((\d+\s*m?s)\))?$"
    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status_symbol, test_name, _duration = match.groups()
            if status_symbol == "✔":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status_symbol == "✖":
                test_status_map[test_name] = TestStatus.FAILED.value
            elif status_symbol == "-":
                test_status_map[test_name] = TestStatus.SKIPPED.value
    return test_status_map


@dataclass
class ReactPDFee5c96b8(JavaScriptProfile):
    owner: str = "diegomura"
    repo: str = "react-pdf"
    commit: str = "ee5c96b80326ba4441b71be4c7a85ba9f61d4174"
    test_cmd: str = "./node_modules/.bin/vitest --no-color --reporter verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y pkg-config build-essential libpixman-1-0 libpixman-1-dev libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN yarn install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            for pattern, status in [
                (r"^\s*✓\s(.*)\s\d+ms", TestStatus.PASSED.value),
                (r"^\s*✗\s(.*)\s\d+ms", TestStatus.FAILED.value),
                (r"^\s*✖\s(.*)", TestStatus.FAILED.value),
                (r"^\s*✓\s(.*)", TestStatus.PASSED.value),
            ]:
                match = re.match(pattern, line)
                if match:
                    test_name = match.group(1).strip()
                    test_status_map[test_name] = status
                    break
        return test_status_map


@dataclass
class Markeddbf29d91(JavaScriptProfile):
    owner: str = "markedjs"
    repo: str = "marked"
    commit: str = "dbf29d9171a28da21f06122d643baf4e5d4266d4"
    test_cmd: str = "NO_COLOR=1 node --test"

    @property
    def dockerfile(self):
        return f"""FROM node:24-bullseye
RUN apt update && apt install -y git {X11_DEPS}
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm install
RUN npm test
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        fail_pattern = r"^\s*✖\s(.*?)\s\([\.\d]+ms\)"
        pass_pattern = r"^\s*✔\s(.*?)\s\([\.\d]+ms\)"
        for line in log.split("\n"):
            if re.match(fail_pattern, line):
                test = re.match(fail_pattern, line).group(1)
                test_status_map[test.strip()] = TestStatus.FAILED.value
            elif re.search(pass_pattern, line):
                test = re.match(pass_pattern, line).group(1)
                test_status_map[test.strip()] = TestStatus.PASSED.value
        return test_status_map


@dataclass
class Babel2ea3fc8f(JavaScriptProfile):
    owner: str = "babel"
    repo: str = "babel"
    commit: str = "2ea3fc8f9b33a911840f17fbc407e7bfae2ed66f"
    test_cmd: str = "yarn jest --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN make bootstrap
RUN make build
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)

    def get_test_cmd(self, instance: dict, f2p_only: bool = False):
        if KEY_PATCH not in instance:
            return self.test_cmd, []
        test_folders = []
        for f in PatchSet(instance[KEY_PATCH]):
            parts = f.path.split("/")
            if len(parts) >= 2 and parts[0] == "packages":
                test_folders.append("/".join(parts[:2]))
        return f"{self.test_cmd} {' '.join(test_folders)}", test_folders


@dataclass
class GithubReadmeStats3e974011(JavaScriptProfile):
    owner: str = "anuraghazra"
    repo: str = "github-readme-stats"
    commit: str = "3e97401177143bb35abb42279a13991cbd584ca3"  # Using master branch, can be updated to specific commit hash
    test_cmd: str = "npm test -- --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Mongoose5f57a5bb(JavaScriptProfile):
    owner: str = "Automattic"
    repo: str = "mongoose"
    commit: str = "5f57a5bbb2e8dfed8d04be47cdd17728633c44c1"  # Replace with a specific commit hash
    test_cmd: str = "npm test -- --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


# Register all JavaScript profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaScriptProfile)
        and obj.__name__ != "JavaScriptProfile"
    ):
        global_registry.register_profile(obj)
