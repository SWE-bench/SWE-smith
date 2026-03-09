import json
import re
from dataclasses import dataclass, field

from swesmith.constants import ENV_NAME
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, registry


def parse_log_rspec_json(log: str) -> dict[str, str]:
    """Parse RSpec JSON output (from --format json) into a test status map.

    Extracts the JSON object from the log (which may contain other output
    before/after) and maps each example's full_description to PASSED/FAILED.
    """
    # Find the start of the RSpec JSON — look for {"version" or {"examples"
    match = re.search(r"\{\"(?:version|examples)", log)
    if not match:
        return {}
    start = match.start()
    # Find the last closing brace and try to parse from start to there.
    # RSpec JSON can be very large (10MB+), so avoid character-by-character walks.
    end = log.rfind("}")
    if end < start:
        return {}

    try:
        data = json.loads(log[start : end + 1])
    except json.JSONDecodeError:
        return {}

    test_status_map = {}
    for example in data.get("examples", []):
        desc = example.get("full_description", "").strip()
        if not desc:
            continue
        status = example.get("status", "")
        if status == "passed":
            test_status_map[desc] = TestStatus.PASSED.value
        elif status == "failed":
            test_status_map[desc] = TestStatus.FAILED.value
    return test_status_map


def parse_log_ruby_test(log: str) -> dict[str, str]:
    """Parse Ruby test output in either Minitest or test-unit verbose format.

    Minitest verbose:
        TestClass#test_name = X.XX s = .

    test-unit verbose (--verbose):
        TestClassName:
          test_name:     .: (0.001234)
          test_other:    F: (0.002345)
    """
    test_status_map = {}
    current_class = None
    for line in log.splitlines():
        stripped = line.strip()
        # Minitest verbose: "TestClass#test_name = X.XX s = ."
        if "#test_" in stripped and " = " in stripped:
            parts = stripped.rsplit(" = ", 1)
            if len(parts) == 2:
                status_char = parts[1].strip()
                test_name = parts[0].rsplit(" = ", 1)[0].strip()
                if status_char == ".":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif status_char == "F":
                    test_status_map[test_name] = TestStatus.FAILED.value
                elif status_char == "E":
                    test_status_map[test_name] = TestStatus.ERROR.value
            continue
        # test-unit: class header line like "TestClassName:"
        if stripped.endswith(":") and stripped[0].isupper() and " " not in stripped:
            current_class = stripped[:-1]
            continue
        # test-unit verbose: "  test_name:   .: (0.001234)"
        if current_class and (
            ".: (" in stripped or "F: (" in stripped or "E: (" in stripped
        ):
            match = re.match(r"^(\S+):\s+([.FE]):\s+\(", stripped)
            if match:
                test_name = f"{current_class}#{match.group(1)}"
                status_char = match.group(2)
                if status_char == ".":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif status_char == "F":
                    test_status_map[test_name] = TestStatus.FAILED.value
                elif status_char == "E":
                    test_status_map[test_name] = TestStatus.ERROR.value
    return test_status_map


@dataclass
class RubyProfile(RepoProfile):
    """Profile for Ruby repositories."""

    test_cmd: str = "bundle exec rake test"
    exts: list[str] = field(default_factory=lambda: [".rb"])
    ruby_version: str = "3.3"

    def extract_entities(
        self,
        dirs_exclude: list[str] | None = None,
        dirs_include: list[str] = [],
        exclude_tests: bool = True,
        max_entities: int = -1,
    ) -> list:
        """Override to exclude Ruby-specific vendored/generated directories."""
        if dirs_exclude is None:
            dirs_exclude = [
                "vendor",
                ".bundle",
                "tmp",
                "pkg",
                "doc",
                "coverage",
            ]

        return super().extract_entities(
            dirs_exclude=dirs_exclude,
            dirs_include=dirs_include,
            exclude_tests=exclude_tests,
            max_entities=max_entities,
        )

    def _is_test_path(self, root: str, file: str) -> bool:
        if super()._is_test_path(root, file):
            return True
        dirs = root.split("/")
        if "spec" in dirs:
            return True
        if file.endswith("_spec.rb"):
            return True
        return False

    def log_parser(self, log: str):
        # Try RSpec JSON first (repos using --format json)
        result = parse_log_rspec_json(log)
        if result:
            return result
        # Fall back to Minitest/test-unit verbose format
        return parse_log_ruby_test(log)

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


# SWE-bench_Multilingual repos


@dataclass
class Faker9ef1ecae(RubyProfile):
    owner: str = "faker-ruby"
    repo: str = "faker"
    commit: str = "9ef1ecae1fcf90f2f244c50593a6da366399c337"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )


@dataclass
class Rubocop519206df(RubyProfile):
    owner: str = "rubocop"
    repo: str = "rubocop"
    commit: str = "519206df11583194be0f9eea55c641c8da905fa4"
    test_cmd: str = "bundle exec rspec --format json"
    timeout: int = 180
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )


@dataclass
class Jekylld0cf1791(RubyProfile):
    owner: str = "jekyll"
    repo: str = "jekyll"
    commit: str = "d0cf1791f6a349519998750f4511822e43e516e4"
    test_cmd: str = "bundle exec rake test"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )


@dataclass
class Fluentd7906fda4(RubyProfile):
    owner: str = "fluent"
    repo: str = "fluentd"
    commit: str = "7906fda46092a6d997bef0a1608d21e4c38634df"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
    libyajl-dev libev-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


@dataclass
class Fastlane0e18ea7c(RubyProfile):
    owner: str = "fastlane"
    repo: str = "fastlane"
    commit: str = "0e18ea7cbdabef25e2b6ec2748a674aabf9dcf03"
    test_cmd: str = "bundle exec rspec --format json"
    timeout: int = 300
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )


@dataclass
class Fpm5b1fe9af(RubyProfile):
    owner: str = "jordansissel"
    repo: str = "fpm"
    commit: str = "5b1fe9afe446cf0384606ed061cdfea44c966420"
    test_cmd: str = "bundle exec rspec --format json"
    eval_sets: set[str] = field(
        default_factory=lambda: {"SWE-bench/SWE-bench_Multilingual"}
    )

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
    rpm squashfs-tools \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


# Additional repos (alphabetical by repo name)


@dataclass
class Brakeman2e55d45a(RubyProfile):
    owner: str = "presidentbeef"
    repo: str = "brakeman"
    commit: str = "2e55d45a9770ee570005400df074d18e8fdb8c3a"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"
    timeout: int = 180


@dataclass
class ConcurrentRuby30dc89e4(RubyProfile):
    owner: str = "ruby-concurrency"
    repo: str = "concurrent-ruby"
    commit: str = "30dc89e4c7b61833126d762a9d6cec8de937d35f"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class Csvbc698274(RubyProfile):
    owner: str = "ruby"
    repo: str = "csv"
    commit: str = "bc69827460390a0224616b5ad1949dec01a3404d"
    test_cmd: str = "bundle exec rake test"


@dataclass
class Devise5b008ed5(RubyProfile):
    owner: str = "heartcombo"
    repo: str = "devise"
    commit: str = "5b008ed51c0df3223cf727e7ad07378d6329b12f"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
    libsqlite3-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


@dataclass
class DryValidation4a165232(RubyProfile):
    owner: str = "dry-rb"
    repo: str = "dry-validation"
    commit: str = "4a165232df192a4f71b2a6eac5013cc3bbfbe9fc"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class FactoryBot8a64d293(RubyProfile):
    owner: str = "thoughtbot"
    repo: str = "factory_bot"
    commit: str = "8a64d2938fd2269fb55c7e4794ca07cf045ad2f7"
    test_cmd: str = "bundle exec rspec --format json"

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
    libsqlite3-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


@dataclass
class Foremanf65ddba8(RubyProfile):
    owner: str = "ddollar"
    repo: str = "foreman"
    commit: str = "f65ddba83932bd4670e014389d6e27ea1e20b469"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class Grapef2fc392d(RubyProfile):
    owner: str = "ruby-grape"
    repo: str = "grape"
    commit: str = "f2fc392dcae0c1e1fbf4196fa3f51a024e7f22db"
    test_cmd: str = "bundle exec rspec --format json"
    timeout: int = 180


@dataclass
class Hashie3988742e(RubyProfile):
    owner: str = "hashie"
    repo: str = "hashie"
    commit: str = "3988742ebc7edb0500c67c4463ce54cd318d7af9"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class Liquidd897899f(RubyProfile):
    owner: str = "Shopify"
    repo: str = "liquid"
    commit: str = "d897899f6654c476e58e884bc8e24924600e5801"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"
    timeout: int = 180


@dataclass
class Pry13564026(RubyProfile):
    owner: str = "pry"
    repo: str = "pry"
    commit: str = "135640262879544c6bfecbf3e78511289bfe956c"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class Punditd53c8414(RubyProfile):
    owner: str = "varvet"
    repo: str = "pundit"
    commit: str = "d53c8414e4c1a096585a036ea7c1ac1b22dac417"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class Rack75c5745c(RubyProfile):
    owner: str = "rack"
    repo: str = "rack"
    commit: str = "75c5745c286637a8f049a33790c71237762069e7"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"


@dataclass
class Simplecov522dc7d3(RubyProfile):
    owner: str = "simplecov-ruby"
    repo: str = "simplecov"
    commit: str = "522dc7d3aee12084a80680dcb014580ed156e988"
    test_cmd: str = "bundle exec rspec --format json"


@dataclass
class Sinatra9e5c4ec8(RubyProfile):
    owner: str = "sinatra"
    repo: str = "sinatra"
    commit: str = "9e5c4ec8ade92c7375f44acf4c6e1103d32d6c12"
    test_cmd: str = "bundle exec rake test TESTOPTS='--verbose'"
    timeout: int = 180

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
    libxml2-dev libxslt-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


@dataclass
class Vcr9a66a8a0(RubyProfile):
    owner: str = "vcr"
    repo: str = "vcr"
    commit: str = "9a66a8a0e452fa09eec71045004b86cbf5cd131b"
    test_cmd: str = "bundle exec rspec --format json"

    @property
    def dockerfile(self):
        return f"""FROM ruby:{self.ruby_version}
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y wget git build-essential \
    libcurl4-openssl-dev \
&& rm -rf /var/lib/apt/lists/*

RUN git clone {self.mirror_url} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN bundle install || true
RUN {self.test_cmd} || true
"""


# Register all Ruby profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, RubyProfile)
        and obj.__name__ != "RubyProfile"
    ):
        registry.register_profile(obj)
