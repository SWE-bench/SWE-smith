import re
import subprocess

from swebench.harness.constants import TestStatus
from swesmith.constants import LOG_DIR_ENV
from swesmith.profiles.base import RepoProfile, global_registry


class Gin3c12d2a8(RepoProfile):
    owner = "gin-gonic"
    repo = "gin"
    commit = "3c12d2a80e40930632fc4a4a4e1a45140f33fb12"
    test_cmd = "go test -v ./..."

    def build_image(self):
        dockerfile = f"""FROM golang:1.24
RUN git clone https://github.com/{self.org_gh}/{self.get_mirror_name()} /testbed
WORKDIR /testbed
RUN go mod tidy
RUN go test ./...
"""
        env_dir = LOG_DIR_ENV / self.get_image_name()
        env_dir.mkdir(parents=True, exist_ok=True)
        dockerfile_path = env_dir / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile)
        with open("build_image.log", "w") as log_file:
            subprocess.run(
                f"docker build -f {dockerfile_path} -t {self.get_image_name()} .",
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )

    def log_parser(self, log: str) -> dict[str, str]:
        """Parser for test logs generated with 'go test'"""
        test_status_map = {}

        # Pattern to match test result lines
        pattern = r"^--- (PASS|FAIL|SKIP): (.+) \((.+)\)$"

        for line in log.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                status, test_name, _duration = match.groups()
                if status == "PASS":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif status == "FAIL":
                    test_status_map[test_name] = TestStatus.FAILED.value
                elif status == "SKIP":
                    test_status_map[test_name] = TestStatus.SKIPPED.value

        return test_status_map


# Register all Go profiles with the global registry
global_registry.register_from_module(RepoProfile, globals())
