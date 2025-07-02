"""
This file is used to store common installation or testing patterns that may be
reused across different repositories / languages.
"""

CMAKE_VERSIONS = ["3.15.7", "3.16.9", "3.17.5", "3.19.7", "3.23.5", "3.27.9"]
INSTALL_CMAKE = (
    [
        f"wget https://github.com/Kitware/CMake/releases/download/v{v}/cmake-{v}-Linux-x86_64.tar.gz"
        for v in CMAKE_VERSIONS
    ]
    + [
        f"tar -xvzf cmake-{v}-Linux-x86_64.tar.gz && mv cmake-{v}-Linux-x86_64 /usr/share/cmake-{v}"
        if v not in ["3.23.5", "3.27.9"]
        else f"tar -xvzf cmake-{v}-Linux-x86_64.tar.gz && mv cmake-{v}-linux-x86_64 /usr/share/cmake-{v}"
        for v in CMAKE_VERSIONS
    ]
    + [
        f"update-alternatives --install /usr/bin/cmake cmake /usr/share/cmake-{v}/bin/cmake {(idx + 1) * 10}"
        for idx, v in enumerate(CMAKE_VERSIONS)
    ]
)

INSTALL_BAZEL = [
    cmd
    for v in ["6.5.0", "7.4.1", "8.0.0"]
    for cmd in [
        f"mkdir -p /usr/share/bazel-{v}/bin",
        f"wget https://github.com/bazelbuild/bazel/releases/download/{v}/bazel-{v}-linux-x86_64",
        f"chmod +x bazel-{v}-linux-x86_64",
        f"mv bazel-{v}-linux-x86_64 /usr/share/bazel-{v}/bin/bazel",
    ]
]

X11_DEPS = " ".join(
    [
        "libx11-xcb1",
        "libxcomposite1",
        "libxcursor1",
        "libxdamage1",
        "libxi6",
        "libxtst6",
        "libnss3",
        "libcups2",
        "libxss1",
        "libxrandr2",
        "libasound2",
        "libatk1.0-0",
        "libgtk-3-0",
        "x11-utils",
    ]
)
