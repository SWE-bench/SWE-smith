import re
import sys
from pathlib import Path

from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, registry

# Import log parsers from mini-swe-agent-automate-repo-installation
_log_parser_path = Path(__file__).parent.parent.parent / "mini-swe-agent-automate-repo-installation"
if _log_parser_path.exists() and str(_log_parser_path) not in sys.path:
    sys.path.insert(0, str(_log_parser_path))
    
try:
    from log_parser.parsers.maven import parse_log_maven
except ImportError:
    # Fallback if log_parser is not available
    parse_log_maven = None

# Auto-generated profile for JSQLParser/JSqlParser
# Commit: 01034cd08c3e9d75692abb5f8afc9cee97700dad
# Generated: 2025-10-31T12:14:13.756680
# Integration: Copy to swesmith/profiles/java.py




@dataclass
class JavaProfile(RepoProfile):
    """
    Profile for Java repositories.
    """
@dataclass
class JSqlParser01034cd0(JavaProfile):
    owner: str = "JSQLParser"
    repo: str = "JSqlParser"
    commit: str = "01034cd08c3e9d75692abb5f8afc9cee97700dad"
    org_gh: str = "cs329a-swesmith-repos"  # Use custom GitHub org for mirror
    org_dh: str = "cs329a-swesmith"  # Custom Docker Hub org (local builds only)
    test_cmd: str = "./gradlew test --continue --no-daemon || true; find build/test-results/test -type f -name '*.xml' -exec cat {} \\;"
    timeout: int = 300  # Test execution timeout

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk
RUN apt-get update && apt-get install -y git procps && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN chmod +x gradlew
RUN ./gradlew build -x test --no-daemon || true
"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        import re
        import xml.etree.ElementTree as ET

        test_status_map = {}

        # Extract XML content from the log
        xml_matches = re.findall(r'<\?xml version.*?</testsuite>', log, re.DOTALL)  

        for xml_content in xml_matches:
            try:
                root = ET.fromstring(xml_content)
                suite_classname = root.get('name', '')

                # Parse each testcase
                for testcase in root.findall('.//testcase'):
                    classname = testcase.get('classname', suite_classname)
                    methodname = testcase.get('name', '')
                    test_name = f"{classname}.{methodname}"

                    # Check for failure, error, or skipped
                    if testcase.find('failure') is not None or testcase.find('error') is not None:
                        test_status_map[test_name] = TestStatus.FAILED.value        
                    elif testcase.find('skipped') is not None:
                        test_status_map[test_name] = TestStatus.SKIPPED.value       
                    else:
                        test_status_map[test_name] = TestStatus.PASSED.value        
            except ET.ParseError:
                continue

        return test_status_map


@dataclass
class Keystoreexplorera52ede42(JavaProfile):
    owner: str = "kaikramer"
    repo: str = "keystore-explorer"
    commit: str = "a52ede42c153928c9b594dc7291fcdc71ce02432"
    org_gh: str = "cs329a-swesmith-repos"  # Use custom GitHub org for mirror
    org_dh: str = "cs329a-swesmith"  # Custom Docker Hub org (local builds only)
    test_cmd: str = "/bin/bash -c 'cd kse && ./gradlew test --continue --no-daemon || true; find build/test-results/test -type f -name \"TEST-*.xml\" -exec cat {} \\;'"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM openjdk:17-jdk-slim
RUN apt-get update && apt-get install -y git procps && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed/kse
RUN chmod +x gradlew
RUN ./gradlew clean build -x test --no-daemon || true
"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        import re
        import xml.etree.ElementTree as ET
        
        test_status_map = {}
        
        # Extract XML content from the log
        xml_matches = re.findall(r'<\?xml version.*?</testsuite>', log, re.DOTALL)
        
        for xml_content in xml_matches:
            try:
                root = ET.fromstring(xml_content)
                suite_classname = root.get('name', '')
                
                # Parse each testcase
                for testcase in root.findall('.//testcase'):
                    classname = testcase.get('classname', suite_classname)
                    methodname = testcase.get('name', '')
                    test_name = f"{classname}.{methodname}"
                    
                    # Check for failure, error, or skipped
                    if testcase.find('failure') is not None or testcase.find('error') is not None:
                        test_status_map[test_name] = TestStatus.FAILED.value
                    elif testcase.find('skipped') is not None:
                        test_status_map[test_name] = TestStatus.SKIPPED.value
                    else:
                        test_status_map[test_name] = TestStatus.PASSED.value
            except ET.ParseError:
                continue
        
        return test_status_map

# Auto-generated profile for google/gson (java)
# Commit: 50a93686df9e49dd20fecff222bb9ca169a29754
# Generated: 2025-11-10T13:41:37.567564
# Integration: Copy to swesmith/profiles/java.py


# Auto-generated profile for google/gson (java)
# Commit: 50a93686df9e49dd20fecff222bb9ca169a29754
# Generated: 2025-11-10T14:01:53.234192
# Integration: Copy to swesmith/profiles/java.py

# @dataclass
# class Gson50a93686(JavaProfile):
#     owner: str = "google"
#     repo: str = "gson"
#     commit: str = "50a93686df9e49dd20fecff222bb9ca169a29754"
#     org_gh: str = "cs329a-swesmith-repos"  # Custom GitHub org for mirror
#     org_dh: str = "cs329a-swesmith"  # Custom Docker Hub org
#     test_cmd: str = "mvn test -B -pl gson,extras,metrics"

#     @property
#     def dockerfile(self):
#         return f"""FROM openjdk:17
# RUN apt-get update && apt-get install -y git
# RUN git clone https://github.com/{self.mirror_name} /testbed
# WORKDIR /testbed
# """

#     def log_parser(self, log: str) -> dict[str, str]:
#         """Parse Maven Surefire test output."""
#         # Note: parse_log_maven should be imported at top of file
#         if parse_log_maven is not None:
#             return parse_log_maven(log)
#         return {}

@dataclass
class Gsondd2fe59c(JavaProfile):
    owner: str = "google"
    repo: str = "gson"
    commit: str = "dd2fe59c0d3390b2ad3dd365ed6938a5c15844cb"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Dmaven.compiler.failOnWarning=false"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

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
        registry.register_profile(obj)
