import re

from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class JavaProfile(RepoProfile):
    """
    Profile for Java repositories.
    """


@dataclass
class Gsondd2fe59c(JavaProfile):
    owner: str = "google"
    repo: str = "gson"
    commit: str = "dd2fe59c0d3390b2ad3dd365ed6938a5c15844cb"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"

    @property
    def dockerfile(self):
        return f"""FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y git openjdk-11-jdk
RUN apt-get install -y maven
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN mvn clean install -B -pl gson -DskipTests -am
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        pattern = r"^\[(INFO|ERROR)\]\s+(.*?)\s+--\s+Time elapsed:\s+([\d.]+)\s"
        for line in log.split("\n"):
            if line.endswith("<<< FAILURE!") and line.startswith("[ERROR]"):
                test_name = re.match(pattern, line)
                if test_name is None:
                    continue
                test_status_map[test_name.group(2)] = TestStatus.FAILED.value
            elif (
                any([line.startswith(s) for s in ["[INFO]", "[ERROR]"]])
                and "Time elapsed:" in line
            ):
                test_name = re.match(pattern, line)
                if test_name is None:
                    continue
                test_status_map[test_name.group(2)] = TestStatus.PASSED.value
        return test_status_map


# Register all Java profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaProfile)
        and obj.__name__ != "JavaProfile"
    ):
        global_registry.register_profile(obj)
