from dataclasses import dataclass
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class CProfile(RepoProfile):
    """
    Profile for C repositories.
    """


# Register all C profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, CProfile)
        and obj.__name__ != "CProfile"
    ):
        registry.register_profile(obj)
