from dataclasses import dataclass
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class JavaProfile(RepoProfile):
    """
    Profile for Java repositories.
    """


# Register all Java profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, JavaProfile)
        and obj.__name__ != "JavaProfile"
    ):
        registry.register_profile(obj)
