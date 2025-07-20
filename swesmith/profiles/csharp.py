from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class CSharpProfile(RepoProfile):
    """
    Profile for CSharp repositories.
    """


@dataclass
class VirtualClient0bb16489(CSharpProfile):
    owner: str = "microsoft"
    repo: str = "VirtualClient"
    commit: str = "0bb16489e29d2b8ae18b1187ade52cda4eae68bd"
    test_cmd: str = "./build-test.sh"

    @property
    def dockerfile(self):
        return f"""FROM mcr.microsoft.com/devcontainers/dotnet:dev-9.0-noble
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN chmod +x *.sh \
 && ./build.sh \
 && (./build-test.sh || true)
CMD ["/bin/bash"]
"""

    def _is_test_path(self, root: str, file: str) -> bool:
        return (
            file.endswith("Tests.cs")
            or root.endswith(".UnitTests")
            or root.endswith(".FunctionalTests")
        )

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            line = line.strip()
            for prefix, status in [
                ("Passed", TestStatus.PASSED.value),
                ("Failed", TestStatus.FAILED.value),
                ("Skipped", TestStatus.SKIPPED.value),
            ]:
                if line.startswith(prefix):
                    test_name = line.split()[1]
                    test_status_map[test_name] = status
                    break
        return test_status_map


# Register all CSharp profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, CSharpProfile)
        and obj.__name__ != "CSharpProfile"
    ):
        global_registry.register_profile(obj)
