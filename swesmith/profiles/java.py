import re
import xml.etree.ElementTree as ET

from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.constants import ENV_NAME
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class JavaProfile(RepoProfile):
    """
    Profile for Java repositories.
    """

    exts: list[str] = field(default_factory=lambda: [".java"])


def parse_log_maven_surefire(log: str) -> dict[str, str]:
    """
    Parse Maven Surefire text output with per-method granularity.

    Handles two formats:
    1. With [INFO]/[ERROR] prefix: [INFO] testMethodName -- Time elapsed: 0.001 s
    2. Without prefix: testMethodName(className)  Time elapsed: 0.001 sec

    Used with: mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain

    Args:
        log (str): log content from Maven Surefire
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    # Pattern 1: [INFO] testMethodName -- Time elapsed: 0.001 s
    # Pattern 2: [ERROR] testMethodName -- Time elapsed: 0.001 s <<< FAILURE!
    pattern_with_prefix = r"^\[(INFO|ERROR)\]\s+(.*?)\s+--\s+Time elapsed:\s+([\d.]+)\s"

    # Pattern 3: testMethodName(className)  Time elapsed: 0.001 sec
    # Pattern 4: testMethodName(className)  Time elapsed: 0 sec
    pattern_no_prefix = (
        r"^([a-zA-Z0-9_]+)\(([a-zA-Z0-9_.]+)\)\s+Time elapsed:\s+([\d.]+)\s+sec"
    )

    for line in log.split("\n"):
        line = line.strip()

        # Try pattern with [INFO]/[ERROR] prefix first
        if line.startswith("["):
            if line.endswith("<<< FAILURE!") and line.startswith("[ERROR]"):
                test_name = re.match(pattern_with_prefix, line)
                if test_name:
                    test_status_map[test_name.group(2)] = TestStatus.FAILED.value
            elif "Time elapsed:" in line:
                test_name = re.match(pattern_with_prefix, line)
                if test_name:
                    test_status_map[test_name.group(2)] = TestStatus.PASSED.value

        # Try pattern without prefix
        elif "Time elapsed:" in line and "(" in line:
            match = re.match(pattern_no_prefix, line)
            if match:
                test_method = match.group(1)
                test_class = match.group(2)
                test_name = f"{test_class}.{test_method}"
                test_status_map[test_name] = TestStatus.PASSED.value

    return test_status_map


def parse_log_gradle_junit_xml(log: str) -> dict[str, str]:
    """
    Parse JUnit XML test results from Gradle output.

    Parses XML testsuite elements from Gradle test output when using:
    ./gradlew test ... || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;

    Args:
        log (str): log content containing JUnit XML test results
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    xml_matches = re.findall(r"<\?xml version.*?</testsuite>", log, re.DOTALL)

    for xml_content in xml_matches:
        try:
            root = ET.fromstring(xml_content)
            suite_classname = root.get("name", "")

            for testcase in root.findall(".//testcase"):
                classname = testcase.get("classname", suite_classname)
                methodname = testcase.get("name", "")
                test_name = f"{classname}.{methodname}"

                if (
                    testcase.find("failure") is not None
                    or testcase.find("error") is not None
                ):
                    test_status_map[test_name] = TestStatus.FAILED.value
                elif testcase.find("skipped") is not None:
                    test_status_map[test_name] = TestStatus.SKIPPED.value
                else:
                    test_status_map[test_name] = TestStatus.PASSED.value
        except ET.ParseError:
            continue

    return test_status_map


@dataclass
class Gsondd2fe59c(JavaProfile):
    owner: str = "google"
    repo: str = "gson"
    commit: str = "dd2fe59c0d3390b2ad3dd365ed6938a5c15844cb"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
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
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -pl gson -DskipTests -am
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_maven_surefire(log)


@dataclass
class Mindustry2ad41a90(JavaProfile):
    owner: str = "Anuken"
    repo: str = "Mindustry"
    commit: str = "2ad41a904753a47f6fb1a7b64dbea46204ce207e"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew --no-daemon --console=plain assemble -x test

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Asynchttpclientae59f51f(JavaProfile):
    owner: str = "AsyncHttpClient"
    repo: str = "async-http-client"
    commit: str = "ae59f51f70b2ad99601c0a0c23d8c6e9260a0400"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.8-eclipse-temurin-11

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -DskipTests -Dgpg.skip
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Recaf2a93d630(JavaProfile):
    owner: str = "Col-E"
    repo: str = "Recaf"
    commit: str = "2a93d6306f6809532cb7b50a5091f3599d3971cb"
    test_cmd: str = "./gradlew :recaf-core:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:22-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew :recaf-core:build -x test --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class HMCL79a1c3af(JavaProfile):
    owner: str = "HMCL-dev"
    repo: str = "HMCL"
    commit: str = "79a1c3af8aed91fc6298cd17aff2592cd9a3e0ee"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew --no-daemon --console=plain assemble -x test

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Web3j37d9bc9b(JavaProfile):
    owner: str = "LFDT-web3j"
    repo: str = "web3j"
    commit: str = "37d9bc9bef85bd45c9b64cbf023eaf89df21f300"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Disruptorc871ca49(JavaProfile):
    owner: str = "LMAX-Exchange"
    repo: str = "disruptor"
    commit: str = "c871ca49826a6be7ada6957f6fbafcfecf7b1f87"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class MycatServer243539fb(JavaProfile):
    owner: str = "MyCATApache"
    repo: str = "Mycat-Server"
    commit: str = "243539fb74bbdcb9819fecc7e7b50ccf0899e671"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8-openjdk-8-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Eureka459fcf59(JavaProfile):
    owner: str = "Netflix"
    repo: str = "eureka"
    commit: str = "459fcf59866b1a950f6e88530a0b1b870fa5212f"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew build -x test --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Paper81b91224(JavaProfile):
    owner: str = "PaperMC"
    repo: str = "Paper"
    commit: str = "81b9122470121035de76325592a9cf84208fac55"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Paper uses a complex build system that often requires initializing submodules or running setup scripts.
# We run gradlew help to trigger wrapper download and basic initialization.
RUN ./gradlew --no-daemon --console=plain help

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class MPAndroidChart9c7275a0(JavaProfile):
    owner: str = "PhilJay"
    repo: str = "MPAndroidChart"
    commit: str = "9c7275a0596a7ac0e50ca566e680f7f9d73607af"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM runmymind/docker-android-sdk:latest

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assembleDebug --no-daemon --console=plain
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class RxAndroidd7bd9b74(JavaProfile):
    owner: str = "ReactiveX"
    repo: str = "RxAndroid"
    commit: str = "d7bd9b74f405f2030a086d754190db430087c24f"
    test_cmd: str = "./gradlew :rxandroid:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y \
    openjdk-11-jdk-headless \
    git \
    wget \
    unzip \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p ${{ANDROID_SDK_ROOT}}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-7583922_latest.zip -O /tmp/tools.zip && \
    unzip -q /tmp/tools.zip -d ${{ANDROID_SDK_ROOT}}/cmdline-tools && \
    mv ${{ANDROID_SDK_ROOT}}/cmdline-tools/cmdline-tools ${{ANDROID_SDK_ROOT}}/cmdline-tools/latest && \
    rm /tmp/tools.zip

ENV PATH=${{PATH}}:${{ANDROID_SDK_ROOT}}/cmdline-tools/latest/bin:${{ANDROID_SDK_ROOT}}/platform-tools

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN yes | sdkmanager --licenses && \
    sdkmanager "platforms;android-31" "build-tools;31.0.0"

# Only build the library module to avoid AAPT2 issues with the sample app on ARM
RUN ./gradlew :rxandroid:assembleDebug --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class GoGoGode0d5961(JavaProfile):
    owner: str = "ZCShou"
    repo: str = "GoGoGo"
    commit: str = "de0d596190c57b8ca71481f60ce6b9e50af5107f"
    test_cmd: str = "./gradlew testDebugUnitTest --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM --platform=linux/amd64 eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git wget unzip && rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p $ANDROID_SDK_ROOT/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O /tmp/tools.zip && \
    unzip -q /tmp/tools.zip -d $ANDROID_SDK_ROOT/cmdline-tools && \
    mv $ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools $ANDROID_SDK_ROOT/cmdline-tools/latest && \
    rm /tmp/tools.zip

ENV PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools

RUN yes | sdkmanager --licenses
RUN sdkmanager "platforms;android-32" "platform-tools"

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN sed -i 's/..\\\\keystore\\\\GoGoGo.jks/..\\/keystore\\/GoGoGo.jks/g' app/build.gradle
RUN echo "MAPS_API_KEY=unused" > local.properties && echo "MAPS_SAFE_CODE=unused" >> local.properties

RUN sed -i 's/locationOption.setIgnoreCacheException(true);//g' app/src/main/java/com/zcshou/gogogo/MainActivity.java

RUN chmod +x gradlew && ./gradlew assembleDebug --no-daemon --console=plain || true

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Austin4c921ea0(JavaProfile):
    owner: str = "ZhongFuCheng3y"
    repo: str = "austin"
    commit: str = "4c921ea047063c21bdec81f2c98c7d8f61d767af"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl '!austin-data-house'"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -pl '!austin-data-house'

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Mapper3aa82765(JavaProfile):
    owner: str = "abel533"
    repo: str = "Mapper"
    commit: str = "3aa82765670d72627b56735256a5dd1c149b735b"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class QLExpressa632409f(JavaProfile):
    owner: str = "alibaba"
    repo: str = "QLExpress"
    commit: str = "a632409fe7e7b16421a7ea01d4d83060c82158a1"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Druid933dee04(JavaProfile):
    owner: str = "alibaba"
    repo: str = "druid"
    commit: str = "933dee04e7681c42327b440300ed852c905899ff"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8-openjdk-8-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Otter7544d051(JavaProfile):
    owner: str = "alibaba"
    repo: str = "otter"
    commit: str = "7544d0515e832b188736cc6d882d5a7da0558a55"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Denv=release -Dmaven.test.skip=false"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.8-eclipse-temurin-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN cd lib && bash install.sh
RUN mvn clean install -B -q -DskipTests -Denv=release
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Hbase30c42a87(JavaProfile):
    owner: str = "apache"
    repo: str = "hbase"
    commit: str = "30c42a874855b5b012cdaaa15efdff8fa1846bdd"
    test_cmd: str = "mvn test -B -pl hbase-common -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use -pl hbase-common to limit the scope because HBase is massive and might timeout/fail on a full build in some environments
# We will install hbase-common and its dependencies
RUN mvn clean install -B -q -DskipTests -pl hbase-common -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Jmeterb1843c2a(JavaProfile):
    owner: str = "apache"
    repo: str = "jmeter"
    commit: str = "b1843c2a0aa0bc8292cc504e2a0cea53ca373234"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew help --no-daemon --console=plain
# Note: Full build/install of JMeter can be very heavy. 
# We'll use classes to ensure dependencies are downloaded.
RUN ./gradlew classes --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Pulsarc51346fa(JavaProfile):
    owner: str = "apache"
    repo: str = "pulsar"
    commit: str = "c51346fa3f5ec9cdd04ad03ba5d6b05b6c9a4f35"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl pulsar-common"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Pulsar is a massive project. We install a subset (pulsar-common) to ensure the Dockerfile is manageable and builds reliably.
RUN mvn clean install -B -q -DskipTests -pl pulsar-common -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Rocketmq9ad4a1b9(JavaProfile):
    owner: str = "apache"
    repo: str = "rocketmq"
    commit: str = "9ad4a1b94719aa39fd1f1569d739f9978885dc63"
    test_cmd: str = "mvn test -B -pl common,namesrv,srvutil -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Build only a subset of core modules to stay within time limits
RUN mvn clean install -B -q -DskipTests -pl common,namesrv,srvutil -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Seatunneled021460(JavaProfile):
    owner: str = "apache"
    repo: str = "seatunnel"
    commit: str = "ed021460f76b570538685af908f358f09a4be9e9"
    test_cmd: str = "mvn test -B -pl seatunnel-common,seatunnel-api -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.7-eclipse-temurin-11

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -pl seatunnel-common,seatunnel-api -am
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Shardingsphereecf76ffc(JavaProfile):
    owner: str = "apache"
    repo: str = "shardingsphere"
    commit: str = "ecf76ffc4f090c3ca89a6f581de65c5e9320f338"
    test_cmd: str = "mvn test -B -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl infra/common"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Build required modules for infra-common
RUN mvn clean install -B -q -DskipTests -pl infra/common -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Shenyu74954fa2(JavaProfile):
    owner: str = "apache"
    repo: str = "shenyu"
    commit: str = "74954fa2b9e5a8d0426929ad754a78048be32c9f"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.5-openjdk-17-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Mybatisplus9c06ccaf(JavaProfile):
    owner: str = "baomidou"
    repo: str = "mybatis-plus"
    commit: str = "9c06ccaf4a42ec4d96d8494d145be74e3261d700"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew build -x test --no-daemon --console=plain
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Bazel08e077e7(JavaProfile):
    owner: str = "bazelbuild"
    repo: str = "bazel"
    commit: str = "08e077e7a46b5f2137cf3335104219133f8d997f"
    test_cmd: str = 'bazel test //src/test/java/com/google/devtools/build/lib/util:UtilTests --test_output=all --noshow_progress --show_result=10 --test_summary=detailed || true; find bazel-testlogs -name "test.xml" -exec cat {} +'
    timeout: int = 300

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    python3 \
    unzip \
    zip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Bazelisk
RUN curl -L https://github.com/bazelbuild/bazelisk/releases/download/v1.19.0/bazelisk-linux-amd64 -o /usr/local/bin/bazel && \
    chmod +x /usr/local/bin/bazel


# Shallow clone the repository
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Pre-fetch dependencies
RUN bazel fetch //src:bazel

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class HikariCPbba167f0(JavaProfile):
    owner: str = "brettwooldridge"
    repo: str = "HikariCP"
    commit: str = "bba167f0a28905e8e63083cd7b5cbf479263271a"
    test_cmd: str = "mvn test -Ddocker.skip=true -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-11

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -Ddocker.skip=true
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class YCSB6d0fbba2(JavaProfile):
    owner: str = "brianfrankcooper"
    repo: str = "YCSB"
    commit: str = "6d0fbba2de8284db47e943ebcb110ef8dbe3f6bf"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl core"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -pl core -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Btrace3ba0198d(JavaProfile):
    owner: str = "btraceio"
    repo: str = "btrace"
    commit: str = "3ba0198d94d38907cf7e2370bcc1538c8f1227cd"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git openjdk-8-jdk openjdk-11-jdk && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Hutool44836454(JavaProfile):
    owner: str = "chinabugotech"
    repo: str = "hutool"
    commit: str = "448364545257cd1f2df400053f176be7090619bc"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-8

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Thumbnailator068d36e3(JavaProfile):
    owner: str = "coobird"
    repo: str = "thumbnailator"
    commit: str = "068d36e3a1214d0900e50ffc31a18879d01385ce"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9-eclipse-temurin-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Spotless8e776ec8(JavaProfile):
    owner: str = "diffplug"
    repo: str = "spotless"
    commit: str = "8e776ec835b443b2c7d7e9e662aac268fa270050"
    test_cmd: str = "./gradlew :lib:test :testlib:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew :lib:build :testlib:build -x test --no-daemon --console=plain
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Dropwizarde01f4694(JavaProfile):
    owner: str = "dropwizard"
    repo: str = "dropwizard"
    commit: str = "e01f4694724c3fd0be8d62bb2ca22313d2331c89"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Metrics968f367a(JavaProfile):
    owner: str = "dropwizard"
    repo: str = "metrics"
    commit: str = "968f367aa42b33e6b704ebf8d477e385a1d6acbc"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Flowableengine1d9f04bc(JavaProfile):
    owner: str = "flowable"
    repo: str = "flowable-engine"
    commit: str = "1d9f04bcce9dbc786977f2fb311c72aaab5ad080"
    test_cmd: str = "mvn test -B -pl modules/flowable-bpmn-model -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -pl modules/flowable-bpmn-model -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Gephi8f9b9faa(JavaProfile):
    owner: str = "gephi"
    repo: str = "gephi"
    commit: str = "8f9b9faa378ae6ed7231c7a406a2ec0ef29b6d4e"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -PenableTests"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Googlejavaformat737b0032(JavaProfile):
    owner: str = "google"
    repo: str = "google-java-format"
    commit: str = "737b0032b3a18eb6e458271ea440098c166f6c2d"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9-eclipse-temurin-21

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Guice6682b69d(JavaProfile):
    owner: str = "google"
    repo: str = "guice"
    commit: str = "6682b69d081371cceff2a100075a74f41b819a87"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Hibernateorm8cc56928(JavaProfile):
    owner: str = "hibernate"
    repo: str = "hibernate-orm"
    commit: str = "8cc569286809a2a50930eb5c71e3e4b9f9f9f963"
    test_cmd: str = "./gradlew :hibernate-core:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -path '*/test-results/*/TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:25-jdk-noble

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use -x test to skip tests during installation phase
RUN ./gradlew help --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Apktool1981d35b(JavaProfile):
    owner: str = "iBotPeaches"
    repo: str = "Apktool"
    commit: str = "1981d35b832f7e5c94947af6d1f99de336ca8be9"
    test_cmd: str = './gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name "TEST-*.xml" -exec cat {} +'
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Jetlinkscommunity858dab55(JavaProfile):
    owner: str = "jetlinks"
    repo: str = "jetlinks-community"
    commit: str = "858dab5529a35de9cea2261629f5d03e083b320b"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Jsonschema2pojo8c90ed48(JavaProfile):
    owner: str = "joelittlejohn"
    repo: str = "jsonschema2pojo"
    commit: str = "8c90ed48d3c494bcb6cbc5b02a244ccb9169c80d"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.9-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Zxingandroidembeddedd09b7c76(JavaProfile):
    owner: str = "journeyapps"
    repo: str = "zxing-android-embedded"
    commit: str = "d09b7c76c3124fbfbd096a65d60b1997f37ff90f"
    test_cmd: str = "./gradlew :zxing-android-embedded:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git wget unzip libstdc++6 && rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p $ANDROID_SDK_ROOT/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-7583922_latest.zip -O cmdline-tools.zip && \
    unzip -q cmdline-tools.zip -d $ANDROID_SDK_ROOT/cmdline-tools && \
    mv $ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools $ANDROID_SDK_ROOT/cmdline-tools/latest && \
    rm cmdline-tools.zip

ENV PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools

RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-30" "build-tools;30.0.3"

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew :zxing-android-embedded:assembleDebug --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class JsonPathb6c60b3d(JavaProfile):
    owner: str = "json-path"
    repo: str = "JsonPath"
    commit: str = "b6c60b3deef74a83eaa92c8dca7d0bc097e957cd"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class JustAuth694bbf1b(JavaProfile):
    owner: str = "justauth"
    repo: str = "JustAuth"
    commit: str = "694bbf1b010d93404e3bfb4824d90e9ddfaebebb"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Aviatorscript231198d3(JavaProfile):
    owner: str = "killme2008"
    repo: str = "aviatorscript"
    commit: str = "231198d3a8f732ef362841a476f5119df17da83e"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Langchain4j82b882d8(JavaProfile):
    owner: str = "langchain4j"
    repo: str = "langchain4j"
    commit: str = "82b882d885ac87920a2228f9c8b488ea97afa4a0"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl langchain4j-core,langchain4j-open-ai,langchain4j"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Build only core and open-ai modules to keep it manageable and stable
RUN ./mvnw clean install -B -q -DskipTests -pl langchain4j-core,langchain4j-open-ai,langchain4j -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Usbserialforandroida8b9ecc7(JavaProfile):
    owner: str = "mik3y"
    repo: str = "usb-serial-for-android"
    commit: str = "a8b9ecc7d32ce6df749c44a2b9e8cb208ac30609"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM runmymind/docker-android-sdk:latest

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assembleDebug --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class OsmAnd14a13bbc(JavaProfile):
    owner: str = "osmandapp"
    repo: str = "OsmAnd"
    commit: str = "14a13bbc06ab4a60924ed09a66845edbcc2ca317"
    test_cmd: str = "./gradlew :OsmAnd-java:test --rerun-tasks --continue --no-daemon --console=plain --tests 'net.osmand.ReShaperTest' --tests 'net.osmand.util.GeoPointParserUtilTest' --tests 'net.osmand.util.GeoPolylineParserUtilTest' --tests 'net.osmand.util.ParseLengthTest' || true; find OsmAnd-java/build/test-results -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-focal

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Increase memory for Gradle and Java compiler
ENV GRADLE_OPTS="-Xmx2048m -Dorg.gradle.jvmargs='-Xmx2048m -XX:MaxMetaspaceSize=512m'"

RUN ./gradlew :OsmAnd-java:assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Miaoshae5801765(JavaProfile):
    owner: str = "qiurunze123"
    repo: str = "miaosha"
    commit: str = "e58017658e549b63fc4db2160d2325ccd7f8435b"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Dspring-boot.repackage.skip=true -pl miaosha-order/miaosha-order-provider,miaosha-rpc/dubbo-api -am"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN sed -i 's/<packaging>war<\\/packaging>/<packaging>jar<\\/packaging>/g' miaosha-admin/miaosha-admin-service/pom.xml
RUN mvn clean install -B -q -Dmaven.test.skip=true -Dspring-boot.repackage.skip=true

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Quarkus99a220ef(JavaProfile):
    owner: str = "quarkusio"
    repo: str = "quarkus"
    commit: str = "99a220efc4ca53cc5b9d4bb460bf8b97702891bd"
    test_cmd: str = "mvn test -B -pl independent-projects/arc/runtime -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Remove Maven 4/Extension configs
RUN rm -f .mvn/extensions.xml .mvn/maven.config

# Build a simpler module to avoid complex dependency and configuration issues
RUN mvn clean install -B -q -am -pl independent-projects/arc/runtime -DskipTests -Denforcer.skip=true
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Questdb773dd8bf(JavaProfile):
    owner: str = "questdb"
    repo: str = "questdb"
    commit: str = "773dd8bf916b739f6284ea4155821ba713504b61"
    test_cmd: str = "mvn test -B -pl core -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Dtest=io.questdb.test.std.FilesTest,io.questdb.test.std.IntHashSetTest"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-focal

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    build-essential \
    maven \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${{PATH}}"


# Clone the repository
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Install dependencies and build native components
# We use the recommended build profile and skip tests during installation
RUN mvn clean install -B -q -DskipTests -P build-web-console

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Bytebuddy9689261b(JavaProfile):
    owner: str = "raphw"
    repo: str = "byte-buddy"
    commit: str = "9689261b67934371b8f3860a055153e944ea6491"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Reactorcore2198701c(JavaProfile):
    owner: str = "reactor"
    repo: str = "reactor-core"
    commit: str = "2198701c5b88c76080f681741402270305a5c607"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew classes --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Jedis52483b82(JavaProfile):
    owner: str = "redis"
    repo: str = "jedis"
    commit: str = "52483b82738d49d4d0341b30e1901fd9c1d1d414"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Restassureda67ed7ac(JavaProfile):
    owner: str = "rest-assured"
    repo: str = "rest-assured"
    commit: str = "a67ed7ac9d45e1954b151a0e6b87929442cabc54"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class TelegramBots082d9846(JavaProfile):
    owner: str = "rubenlagus"
    repo: str = "TelegramBots"
    commit: str = "082d984628f3d99c63df595786befac4502d86b5"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Dgpg.skip"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests -Dgpg.skip
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class SmartRefreshLayout224db48f(JavaProfile):
    owner: str = "scwang90"
    repo: str = "SmartRefreshLayout"
    commit: str = "224db48f8af897a930b810a6b6fc55af8cef0d57"
    test_cmd: str = "./gradlew :refresh-layout-kernel:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git wget unzip libncurses6 && rm -rf /var/lib/apt/lists/*

# Install Android SDK
ENV ANDROID_HOME=/opt/android-sdk
RUN mkdir -p ${{ANDROID_HOME}}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O cmdline-tools.zip && \
    unzip -q cmdline-tools.zip -d ${{ANDROID_HOME}}/cmdline-tools && \
    mv ${{ANDROID_HOME}}/cmdline-tools/cmdline-tools ${{ANDROID_HOME}}/cmdline-tools/latest && \
    rm cmdline-tools.zip

ENV PATH=${{PATH}}:${{ANDROID_HOME}}/cmdline-tools/latest/bin:${{ANDROID_HOME}}/platform-tools

# Accept licenses
RUN yes | sdkmanager --licenses

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN chmod +x gradlew

# Download dependencies using help task to avoid architecture-specific build failures (AAPT2) during build time
RUN ./gradlew help --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class SignalServer065e7302(JavaProfile):
    owner: str = "signalapp"
    repo: str = "Signal-Server"
    commit: str = "065e730200804c7899ac4458e3dbff82ef678c5c"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:24-jdk-noble

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Jadx331c4aaa(JavaProfile):
    owner: str = "skylot"
    repo: str = "jadx"
    commit: str = "331c4aaa5ef0c6aa97fefafd1a818d5467040bd2"
    test_cmd: str = "./gradlew :jadx-core:test --tests jadx.core.utils.TypeUtilsTest --rerun-tasks --continue -Dorg.gradle.jvmargs=\"-Xmx1024m\" --no-daemon --console=plain || true; find jadx-core/build/test-results/test -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Build specific modules using full task paths to avoid memory issues
RUN ./gradlew :jadx-core:jar :jadx-cli:jar -Dorg.gradle.jvmargs="-Xmx1536m" --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Socketioclientjavaeb438de0(JavaProfile):
    owner: str = "socketio"
    repo: str = "socket.io-client-java"
    commit: str = "eb438de0f7038a075db4c7eff53fd0e7f13116ce"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Dgpg.skip"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && \
    apt-get install -y git maven curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn install -B -q -DskipTests -Dgpg.skip
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Strimzikafkaoperator2d31a2b6(JavaProfile):
    owner: str = "strimzi"
    repo: str = "strimzi-kafka-operator"
    commit: str = "2d31a2b6e7d7c8d333ad14e45ceeab2d52e61525"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git maven wget && \
    wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_$( [ $(uname -m) = "aarch64" ] && echo "arm64" || echo "amd64" ) -O /usr/bin/yq && \
    chmod +x /usr/bin/yq && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -DskipTests -q

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Traccardc1dfe15(JavaProfile):
    owner: str = "traccar"
    repo: str = "traccar"
    commit: str = "dc1dfe15ebc4e75f5855bd21eaba6052cf751624"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Motan4c18b71e(JavaProfile):
    owner: str = "weibocom"
    repo: str = "motan"
    commit: str = "4c18b71e4491200c5cc4317d42556d337f96f11b"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.7-eclipse-temurin-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Zxing50799640(JavaProfile):
    owner: str = "zxing"
    repo: str = "zxing"
    commit: str = "50799640d5c4d6cd85f75f047a3055d05485fae5"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8-openjdk-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Fragmentation0394930a(JavaProfile):
    owner: str = "YoKeyword"
    repo: str = "Fragmentation"
    commit: str = "0394930a3e2368f210df31f2632fb89b9c44e121"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM --platform=linux/amd64 eclipse-temurin:8-jdk-jammy

RUN apt-get update && apt-get install -y git wget unzip libncurses5 && rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV ANDROID_HOME=/opt/android-sdk

RUN mkdir -p $ANDROID_SDK_ROOT/cmdline-tools && \\
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-6858069_latest.zip -O cmdline-tools.zip && \\
    unzip -q cmdline-tools.zip -d $ANDROID_SDK_ROOT/cmdline-tools && \\
    mv $ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools $ANDROID_SDK_ROOT/cmdline-tools/latest && \\
    rm cmdline-tools.zip

ENV PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools

RUN yes | sdkmanager --licenses && \\
    sdkmanager "platform-tools" "platforms;android-28" "build-tools;28.0.3"

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN echo "sdk.dir=$ANDROID_SDK_ROOT" > local.properties

# Android Gradle Plugin 3.2.1/Gradle 4.6 might need this for modern environments
RUN ./gradlew assembleDebug --no-daemon --console=plain -Pandroid.enableAapt2=false || ./gradlew assembleDebug --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Sentinel222670e6(JavaProfile):
    owner: str = "alibaba"
    repo: str = "Sentinel"
    commit: str = "222670e6c38420b15b75527a3120d01afa121be7"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Canalc0619c42(JavaProfile):
    owner: str = "alibaba"
    repo: str = "canal"
    commit: str = "c0619c421723be4b2b4cb61c95cbeb3a2ade5c10"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Dgpg.skip"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8-openjdk-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -Dgpg.skip
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Fastjsonc942c834(JavaProfile):
    owner: str = "alibaba"
    repo: str = "fastjson"
    commit: str = "c942c83443117b73af5ad278cc780270998ba3e1"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Jvmsandboxc01c28ab(JavaProfile):
    owner: str = "alibaba"
    repo: str = "jvm-sandbox"
    commit: str = "c01c28ab5d7d97a64071a2aca261804c47a5347e"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Nacosf39ce37f(JavaProfile):
    owner: str = "alibaba"
    repo: str = "nacos"
    commit: str = "f39ce37f56b6a19df4c6550c89f9d502cbeedb33"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.7-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Calcite84e35baf(JavaProfile):
    owner: str = "apache"
    repo: str = "calcite"
    commit: str = "84e35bafd42784138a2c63cf0c70e1f9744d34d7"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use gradle wrapper to install dependencies. 
# We run help to trigger wrapper download and then build -x test to install deps.
RUN ./gradlew --no-daemon --console=plain help
RUN ./gradlew --no-daemon --console=plain build -x test --continue || true

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Cassandra7fe688b0(JavaProfile):
    owner: str = "apache"
    repo: str = "cassandra"
    commit: str = "7fe688b00096319453afcc5c3da3331816c64072"
    test_cmd: str = "ant test -Dtest.name=StorageServiceTest -Dtest.methods=testBinaryArchive || true; find build/test/output -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git ant ant-optional python3 python3-pip && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Cassandra build can be heavy, we'll run 'ant jar' to download dependencies and build the core
RUN ant jar

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Dubboa92d5d08(JavaProfile):
    owner: str = "apache"
    repo: str = "dubbo"
    commit: str = "a92d5d08d95b7c8fbcc36162f3e03920a519b6b7"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl dubbo-common,dubbo-remoting,dubbo-rpc,dubbo-cluster,dubbo-registry,dubbo-config"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk-focal

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests -pl dubbo-common,dubbo-remoting,dubbo-rpc,dubbo-cluster,dubbo-registry,dubbo-config -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Flinkcdc7d9e1c62(JavaProfile):
    owner: str = "apache"
    repo: str = "flink-cdc"
    commit: str = "7d9e1c627a1e9c85642bba6e8f6fd2d3b2473aa2"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl flink-cdc-common,flink-cdc-pipeline-model,flink-cdc-runtime"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use -pl flink-cdc-common -am to keep the build manageable if needed, 
# but let's try building the core modules.
RUN mvn clean install -B -q -DskipTests -pl flink-cdc-common,flink-cdc-pipeline-model,flink-cdc-runtime -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Hadoop7f2f7149(JavaProfile):
    owner: str = "apache"
    repo: str = "hadoop"
    commit: str = "7f2f7149788005f1dd975ed427d5626abc5145e3"
    test_cmd: str = "mvn test -B -pl hadoop-common-project/hadoop-common -Dtest=TestConfiguration,TestCommonConfigurationKeys -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y \\
    git \\
    maven \\
    build-essential \\
    autoconf \\
    automake \\
    libtool \\
    cmake \\
    zlib1g-dev \\
    pkg-config \\
    libssl-dev \\
    libsasl2-dev \\
    && rm -rf /var/lib/apt/lists/*


# Clone the repository
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Build specific modules to save time and ensure stability in a container environment
# We focus on hadoop-common as it's the core.
RUN mvn clean install -B -q -DskipTests -pl hadoop-common-project/hadoop-common -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Iceberg15485f55(JavaProfile):
    owner: str = "apache"
    repo: str = "iceberg"
    commit: str = "15485f5523d08aae2a503c143c51b6df2debb655"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use assemble to avoid running integration tests during build
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Incubatorkiedroolsfe6decc7(JavaProfile):
    owner: str = "apache"
    repo: str = "incubator-kie-drools"
    commit: str = "fe6decc777e02e22a40e822dd56738c553396f5a"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -Denforcer.skip=true -pl drools-core,drools-compiler"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git wget curl && rm -rf /var/lib/apt/lists/*

ARG MAVEN_VERSION=3.9.9
RUN wget https://archive.apache.org/dist/maven/maven-3/${{MAVEN_VERSION}}/binaries/apache-maven-${{MAVEN_VERSION}}-bin.tar.gz && \\
    tar -xzf apache-maven-${{MAVEN_VERSION}}-bin.tar.gz -C /opt && \\
    ln -s /opt/apache-maven-${{MAVEN_VERSION}}/bin/mvn /usr/bin/mvn && \\
    rm apache-maven-${{MAVEN_VERSION}}-bin.tar.gz

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -Denforcer.skip=true -pl drools-core,drools-compiler -am
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Iotdb36dadf5d(JavaProfile):
    owner: str = "apache"
    repo: str = "iotdb"
    commit: str = "36dadf5d965edcb2b36e62ef28ff914a5327997e"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl iotdb-core/node-commons"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk-focal

RUN apt-get update && apt-get install -y git maven thrift-compiler && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests -am -pl iotdb-api/udf-api,iotdb-api/trigger-api,iotdb-core/node-commons

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Nifiab050e0c(JavaProfile):
    owner: str = "apache"
    repo: str = "nifi"
    commit: str = "ab050e0c3c4f725a32c77d23830bceaaaf271869"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl nifi-commons/nifi-utils"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git maven && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests -pl nifi-commons/nifi-utils -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Storm4bc158f0(JavaProfile):
    owner: str = "apache"
    repo: str = "storm"
    commit: str = "4bc158f0fc4053d82e1bcbfb511447a0ffbe6674"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain -pl storm-client -Dlicense.skip=true -Dcheckstyle.skip -Drat.skip=true"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-focal

RUN apt-get update && apt-get install -y git maven python3 python2 build-essential && \\
    rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use -DskipTests to only install dependencies.
# The multilang modules are needed as dependencies for storm-client
RUN mvn clean install -B -q -DskipTests -Dlicense.skip=true -Dcheckstyle.skip -Drat.skip=true -Denforcer.skip=true

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Dynamicdatasource1d7f40ec(JavaProfile):
    owner: str = "baomidou"
    repo: str = "dynamic-datasource"
    commit: str = "1d7f40ecb4d038392b42f6ca051d039e097318d2"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-focal

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew build -x test --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Bisqf2fe13d0(JavaProfile):
    owner: str = "bisq-network"
    repo: str = "bisq"
    commit: str = "f2fe13d07def5cf7c57f15d0365c2052d3b9f88d"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain -Dorg.gradle.dependency.verification=off || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew build -x test --no-daemon --console=plain -Dorg.gradle.dependency.verification=off

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Tcctransaction874cb910(JavaProfile):
    owner: str = "changmingxie"
    repo: str = "tcc-transaction"
    commit: str = "874cb9105601f0a142f6c428c8fdc4cead851049"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8.5-openjdk-8-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Cate815e74d(JavaProfile):
    owner: str = "dianping"
    repo: str = "cat"
    commit: str = "e815e74d4c2dd74edac831241f1253fcc7d25381"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8-openjdk-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Guava0bf87046(JavaProfile):
    owner: str = "google"
    repo: str = "guava"
    commit: str = "0bf87046267ce281b6335430679fbd59135a1303"
    test_cmd: str = "./mvnw test -B -pl guava-tests -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests -pl guava,guava-tests -am
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Tsunamisecurityscannercf018549(JavaProfile):
    owner: str = "google"
    repo: str = "tsunami-security-scanner"
    commit: str = "cf018549b5e75e5c1a5236b40119424532b06162"
    test_cmd: str = "gradle test --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM gradle:8.5-jdk21

USER root
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN gradle classes --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Hswebframework8c23cc95(JavaProfile):
    owner: str = "hs-web"
    repo: str = "hsweb-framework"
    commit: str = "8c23cc9502e764a04f3cfd83a8a7a49d557a3bfe"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class CalendarViewf5479ea3(JavaProfile):
    owner: str = "huanghaibin-dev"
    repo: str = "CalendarView"
    commit: str = "f5479ea3baefdbba2453cea19a208eca83baeb9e"
    test_cmd: str = "gradle test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk-focal

# Configure multi-arch for AAPT2 (AMD64) on ARM64 host
RUN dpkg --add-architecture amd64 && \\
    sed -i 's/http:\\/\\/ports.ubuntu.com\\/ubuntu-ports/http:\\/\\/archive.ubuntu.com\\/ubuntu/g' /etc/apt/sources.list && \\
    echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports focal main universe restricted multiverse" > /etc/apt/sources.list.d/arm64.list && \\
    echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports focal-updates main universe restricted multiverse" >> /etc/apt/sources.list.d/arm64.list && \\
    echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports focal-security main universe restricted multiverse" >> /etc/apt/sources.list.d/arm64.list && \\
    sed -i 's/^deb /deb [arch=amd64] /' /etc/apt/sources.list && \\
    apt-get update && \\
    apt-get install -y git wget unzip libc6:amd64 libstdc++6:amd64 zlib1g:amd64 && \\
    rm -rf /var/lib/apt/lists/*

# Install Gradle 5.6.4
RUN wget -q https://services.gradle.org/distributions/gradle-5.6.4-bin.zip -O /tmp/gradle.zip && \\
    unzip -q /tmp/gradle.zip -d /opt && \\
    rm /tmp/gradle.zip
ENV GRADLE_HOME=/opt/gradle-5.6.4
ENV PATH=$PATH:$GRADLE_HOME/bin

# Install Android SDK
ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p $ANDROID_SDK_ROOT/cmdline-tools && \\
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O /tmp/tools.zip && \\
    unzip -q /tmp/tools.zip -d $ANDROID_SDK_ROOT/cmdline-tools && \\
    mv $ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools $ANDROID_SDK_ROOT/cmdline-tools/latest && \\
    rm /tmp/tools.zip

ENV PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools

RUN yes | sdkmanager --licenses && \\
    sdkmanager "platform-tools" "platforms;android-28" "build-tools;28.0.3"

# Fix XML validation error in SDK
RUN find $ANDROID_SDK_ROOT -name "package.xml" -exec sed -i '/<base-extension/,/<\\/base-extension>/d' {{}} +

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Fix build scripts and JCenter issues
RUN find . -name "*.gradle" -exec sed -i 's/jcenter()/mavenCentral()/g' {{}} + && \\
    find . -name "*.gradle" -exec sed -i '/com.jfrog.bintray.gradle/d' {{}} + && \\
    find . -name "*.gradle" -exec sed -i "/apply plugin: 'com.jfrog.bintray'/d" {{}} + && \\
    find . -name "*.gradle" -exec sed -i "s/apply from: '..\\/script\\/gradle-jcenter-push.gradle'/\\/\\/ bypassed/g" {{}} + && \\
    echo "sdk.dir=/opt/android-sdk" > local.properties

# Build the project
RUN gradle assembleDebug --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Analysisik9b820257(JavaProfile):
    owner: str = "infinilabs"
    repo: str = "analysis-ik"
    commit: str = "9b820257e288fac34f0d53a7e4439bd21e13600e"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-21

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Mapdb8721c0e8(JavaProfile):
    owner: str = "jankotek"
    repo: str = "mapdb"
    commit: str = "8721c0e824d8d546ecc76639c05ccbc618279511"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:8-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Keycloak051fcab5(JavaProfile):
    owner: str = "keycloak"
    repo: str = "keycloak"
    commit: str = "051fcab5be4b02d47a86ff6e9678584d00e56c39"
    test_cmd: str = "./mvnw test -B -pl core -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Build only the 'core' module and its dependencies to keep the build manageable
RUN ./mvnw clean install -B -q -DskipTests -pl core -am

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Killbillf7d48b59(JavaProfile):
    owner: str = "killbill"
    repo: str = "killbill"
    commit: str = "f7d48b5965cbc1d98805fea499f2e848bd021400"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-11

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Generatorc8cd0c8e(JavaProfile):
    owner: str = "mybatis"
    repo: str = "generator"
    commit: str = "c8cd0c8e3cf387f0d0f357c1151f21f3f3cf8782"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}/core
RUN ./mvnw clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Mybatis359a0bcab(JavaProfile):
    owner: str = "mybatis"
    repo: str = "mybatis-3"
    commit: str = "59a0bcab2b3ebecb2569c1b33173d5ad9c6be152"
    test_cmd: str = "./mvnw test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./mvnw clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class MybatisPageHelperb4212c4d(JavaProfile):
    owner: str = "pagehelper-org"
    repo: str = "Mybatis-PageHelper"
    commit: str = "b4212c4dbd0fa86e4e27cf7a7f6fb9981af305fe"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Plantuml783ae241(JavaProfile):
    owner: str = "plantuml"
    repo: str = "plantuml"
    commit: str = "783ae241f1b33d0e83af89d7e98ca412204803e9"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git graphviz && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew --no-daemon --console=plain classes
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Lettucefa5433c2(JavaProfile):
    owner: str = "redis"
    repo: str = "lettuce"
    commit: str = "fa5433c2750cb6007b07480401a7653b16b013a7"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM --platform=linux/amd64 maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class Picocli121646e4(JavaProfile):
    owner: str = "remkop"
    repo: str = "picocli"
    commit: str = "121646e408bfee65f70875a6ddb94e16e83d958c"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:11-jdk-focal

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew assemble --no-daemon --console=plain
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Runelite6e2d0b20(JavaProfile):
    owner: str = "runelite"
    repo: str = "runelite"
    commit: str = "6e2d0b20caaf9d2195fbd3d02ebde3ab9c3ec246"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use multiple retries for the initial gradle run to ensure the wrapper and dependencies are downloaded
RUN (./gradlew assemble -x test -x javadoc -x checkstyleMain -x checkstyleTest --no-daemon --console=plain || \\
     ./gradlew assemble -x test -x javadoc -x checkstyleMain -x checkstyleTest --no-daemon --console=plain || \\
     ./gradlew assemble -x test -x javadoc -x checkstyleMain -x checkstyleTest --no-daemon --console=plain)
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Springauthorizationserver7d72f556(JavaProfile):
    owner: str = "spring-projects"
    repo: str = "spring-authorization-server"
    commit: str = "7d72f5565cf0c3152caf68e86eb9230d7c19c399"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN ./gradlew classes --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Springbootf73a809c(JavaProfile):
    owner: str = "spring-projects"
    repo: str = "spring-boot"
    commit: str = "f73a809c8c871ed0cf346f4b1a06c0ede4470cc9"
    test_cmd: str = "./gradlew :core:spring-boot:test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} +"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:21-jdk

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use -x javadoc to skip the failing javadoc task
RUN ./gradlew :core:spring-boot:assemble -x javadoc --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


@dataclass
class Javapoetb9017a95(JavaProfile):
    owner: str = "square"
    repo: str = "javapoet"
    commit: str = "b9017a9503b76e11b4ad4c1a9f050e2d29112cb0"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.8-eclipse-temurin-8

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN mvn clean install -B -q -DskipTests
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class CoreNLP1b7edd19(JavaProfile):
    owner: str = "stanfordnlp"
    repo: str = "CoreNLP"
    commit: str = "1b7edd19c4d0d7b1f13a2591425b9b60a0b1af7a"
    test_cmd: str = "mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain"
    timeout: int = 400  # Maven tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM maven:3.9.6-eclipse-temurin-17

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
# Use compile instead of install to avoid trying to move the missing models JAR to the local repo
RUN mvn clean compile -B -q -DskipTests

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse Maven Surefire text output with per-method granularity.

        Parses individual test methods from Maven Surefire output when using:
        mvn test -B -T 1C -Dsurefire.useFile=false -Dsurefire.printSummary=true -Dsurefire.reportFormat=plain
        """
        return parse_log_maven_surefire(log)


@dataclass
class CloudReaderf5b9e67e(JavaProfile):
    owner: str = "youlookwhat"
    repo: str = "CloudReader"
    commit: str = "f5b9e67eef10225d15d3f256da23719b769a8c34"
    test_cmd: str = "./gradlew test --rerun-tasks --continue --no-daemon --console=plain || true; find . -type f -name 'TEST-*.xml' -exec cat {} \\;"
    timeout: int = 300  # Gradle tests can be slow

    @property
    def dockerfile(self):
        return f"""FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update && apt-get install -y git wget unzip && rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p $ANDROID_SDK_ROOT/cmdline-tools && \\
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip -O /tmp/tools.zip && \\
    unzip -q /tmp/tools.zip -d $ANDROID_SDK_ROOT/cmdline-tools && \\
    mv $ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools $ANDROID_SDK_ROOT/cmdline-tools/latest && \\
    rm /tmp/tools.zip

ENV PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools

RUN yes | sdkmanager --licenses && \\
    sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN sed -i 's|distributionUrl=.*|distributionUrl=https\\\\://services.gradle.org/distributions/gradle-8.0-bin.zip|' gradle/wrapper/gradle-wrapper.properties

RUN echo "sdk.dir=/opt/android-sdk" > local.properties

# Verify installation by running dependencies task (skips aapt2)
RUN ./gradlew dependencies --no-daemon --console=plain

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parse JUnit XML test results from Gradle output."""
        return parse_log_gradle_junit_xml(log)


for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaProfile)
        and obj.__name__ != "JavaProfile"
    ):
        registry.register_profile(obj)
