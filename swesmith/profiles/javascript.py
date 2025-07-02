import re

from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry
from swesmith.profiles.utils import X11_DEPS


@dataclass
class JavaScriptProfile(RepoProfile):
    """
    Profile for JavaScript repositories.
    """


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


# Register all Java profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaScriptProfile)
        and obj.__name__ != "JavaScriptProfile"
    ):
        global_registry.register_profile(obj)
