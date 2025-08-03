import re

from dataclasses import dataclass, field
from swesmith.constants import KEY_PATCH
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, registry
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
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

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
    commit: str = "3e97401177143bb35abb42279a13991cbd584ca3"
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
    commit: str = "5f57a5bbb2e8dfed8d04be47cdd17728633c44c1"
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
    commit: str = "ef36347fb559383b04c755b07f1a8d11897fab7f"
    test_cmd: str = "npm run test:mocha -- --verbose"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name)

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Async23dbf76a(JavaScriptProfile):
    owner: str = "caolan"
    repo: str = "async"
    commit: str = "23dbf76aeb04c7c3dd56276115b277e3fa9dd5cc"
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


@dataclass
class Wretch661865a6(JavaScriptProfile):
    owner: str = "elbywan"
    repo: str = "wretch"
    commit: str = "661865a6642f6be26e742a90a3e0a9b9bd5542ff"
    test_cmd: str = "npm run test -- --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm install
RUN npm run build
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Html5Boilerplateac08a17c(JavaScriptProfile):
    owner: str = "h5bp"
    repo: str = "html5-boilerplate"
    commit: str = "ac08a17cb60a975336664c0090657a3e593f686e"
    test_cmd: str = "npm run test -- --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm ci
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class HighlightJS5697ae51(JavaScriptProfile):
    owner: str = "highlightjs"
    repo: str = "highlight.js"
    commit: str = "5697ae5187746c24732e62cd625f3f83004a44ce"
    test_cmd: str = "npm run test -- --verbose"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multimodal"}
    )

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm install
RUN npm run build
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Prism31b467fa(JavaScriptProfile):
    owner: str = "PrismJS"
    repo: str = "prism"
    commit: str = "31b467fa7c92c5ce90c3e7c6c8fe2b8a946d9484"
    test_cmd: str = "npm run test"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multimodal"}
    )

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm ci
RUN npm run build
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class ChromaJS498427ea(JavaScriptProfile):
    owner: str = "gka"
    repo: str = "chroma.js"
    commit: str = "498427eafc2e987a3751f8d5fe0612fa7a4a76ec"
    test_cmd: str = "npm run test -- --run"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN npm install
RUN npm run build
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Colorfef7b619(JavaScriptProfile):
    owner: str = "Qix-"
    repo: str = "color"
    commit: str = "fef7b619edd678455595b9b6a10780f13b58d285"
    test_cmd: str = "npm run test -- --verbose"

    @property
    def image_name(self) -> str:
        # Note: "-" followed by a "_" is not allowed in Docker image names
        return f"{self.org_dh}/swesmith.{self.arch}.{self.owner.replace('-', '_')}_1776_{self.repo}.{self.commit[:8]}".lower()

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name, node_version="22")

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Qd180f4a0(JavaScriptProfile):
    owner: str = "kriskowal"
    repo: str = "q"
    commit: str = "d180f4a0b22499607ac750b56766c8829d6bff43"
    test_cmd: str = "npm run test -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name, node_version="22")

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class ImmutableJS879adab5(JavaScriptProfile):
    owner: str = "immutable-js"
    repo: str = "immutable-js"
    commit: str = "879adab5ea333a5ca341635bcf799c3b8f9e7559"
    test_cmd: str = "npm run test -- --verbose"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name, node_version="22")

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class ThreeJS73b3f248(JavaScriptProfile):
    owner: str = "mrdoob"
    repo: str = "three.js"
    commit: str = "73b3f248016fb73f2fe71da8616cdd7e20386f81"
    test_cmd: str = "npm run test -- --verbose"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name, node_version="22")

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Echarts6be0e145(JavaScriptProfile):
    owner: str = "apache"
    repo: str = "echarts"
    commit: str = "6be0e145946db37824c8635067b8b7b23c547b74"
    test_cmd: str = "npm run test -- --verbose"

    @property
    def dockerfile(self):
        return default_npm_install_dockerfile(self.mirror_name, node_version="22")

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


# Register all JavaScript profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaScriptProfile)
        and obj.__name__ != "JavaScriptProfile"
    ):
        registry.register_profile(obj)
