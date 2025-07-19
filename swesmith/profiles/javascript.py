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


def default_npm_install_dockerfile(mirror_name: str, node_version: str = "18") -> str:
    return f"""FROM node:{node_version}-bullseye
RUN apt update && apt install -y git  
RUN git clone https://github.com/{mirror_name} /testbed
WORKDIR /testbed
RUN npm install
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


def parse_log_vitest(log: str) -> dict[str, str]:
    test_status_map = {}
    patterns = [
        (r"^✓\s+(.+?)(?:\s+\([\.\d]+ms\))?$", TestStatus.PASSED.value),
        (r"^✗\s+(.+?)(?:\s+\([\.\d]+ms\))?$", TestStatus.FAILED.value),
        (r"^○\s+(.+?)(?:\s+\([\.\d]+ms\))?$", TestStatus.SKIPPED.value),
        (r"^✓\s+(.+?)$", TestStatus.PASSED.value),
        (r"^✗\s+(.+?)$", TestStatus.FAILED.value),
        (r"^○\s+(.+?)$", TestStatus.SKIPPED.value),
    ]
    for line in log.split("\n"):
        for pattern, status in patterns:
            match = re.match(pattern, line.strip())
            if match:
                test_name = match.group(1).strip()
                test_status_map[test_name] = status
                break

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
            fail_match = re.match(fail_pattern, line)
            if fail_match:
                test = fail_match.group(1)
                test_status_map[test.strip()] = TestStatus.FAILED.value
            else:
                pass_match = re.match(pass_pattern, line)
                if pass_match:
                    test = pass_match.group(1)
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
        return default_npm_install_dockerfile(self.mirror_name)

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
        return default_npm_install_dockerfile(self.mirror_name)

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Axiosef36347f(JavaScriptProfile):
    owner: str = "axios"
    repo: str = "axios"
    commit: str = "ef36347fb559383b04c755b07f1a8d11897fab7f"  # Replace with a specific commit hash
    test_cmd: str = "npm run test:mocha -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name)

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Async23dbf76a(JavaScriptProfile):
    owner: str = "caolan"
    repo: str = "async"
    commit: str = (
        "23dbf76aeb04c7c3dd56276115b277e3fa9dd5cc"  # Replace with a real commit hash
    )
    test_cmd: str = "npm run mocha-node-test -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name)

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Expressef5f2e13(JavaScriptProfile):
    owner: str = "expressjs"
    repo: str = "express"
    commit: str = "ef5f2e13ef64a1575ce8c2d77b180d593644ccfa"
    test_cmd: str = "npm test -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name)

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Dayjsc8a26460(JavaScriptProfile):
    owner: str = "iamkun"
    repo: str = "dayjs"
    commit: str = "c8a26460d89a2ee9a7d3b9cafa124ea856ee883f"
    test_cmd: str = "npm test -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name)

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Svelte6c9717a9(JavaScriptProfile):
    owner: str = "sveltejs"
    repo: str = "svelte"
    commit: str = "6c9717a91f2f6ae10641d1cf502ba13d227fbe45"
    test_cmd: str = "pnpm test -- --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm@10.4.0
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN pnpm install
RUN pnpm playwright install chromium
RUN pnpm exec playwright install-deps
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Commanderjs395cf714(JavaScriptProfile):
    owner: str = "tj"
    repo: str = "commander.js"
    commit: str = "395cf7145fe28122f5a69026b310e02df114f907"
    test_cmd: str = "npm test -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name, node_version="20")

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


# Register all JavaScript profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaScriptProfile)
        and obj.__name__ != "JavaScriptProfile"
    ):
        global_registry.register_profile(obj)
