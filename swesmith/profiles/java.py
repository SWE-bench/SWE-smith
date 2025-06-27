from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class JavaProfile(RepoProfile):
    """
    Profile for Java repositories.
    """
    
@dataclass
class Dubbo(JavaProfile):
    owner: str = "apache"
    repo: str = "dubbo"
    commit: str = "ea0976b9cbdb5f5e72c4083a32cc9c7e501835b5"
    test_cmd: str = "mvn clean test -Dsurefire.useFile=false -Dmaven.test.skip=false -DfailIfNoTests=false"

    @property
    def dockerfile(self):
        return f"""FROM ubuntu:22.04
RUN apt-get update && \
    apt-get install -y wget git build-essential unzip openjdk-17-jdk maven
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        return test_status_map


# Register all Rust profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaProfile)
        and obj.__name__ != "JavaProfile"
    ):
        global_registry.register_profile(obj)
