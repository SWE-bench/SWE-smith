import re

from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class PhpProfile(RepoProfile):
    """
    Profile for PHP repositories.
    """

    test_cmd: str = "vendor/bin/phpunit --testdox --colors=never"


@dataclass
class Dbal(PhpProfile):
    owner: str = "doctrine"
    repo: str = "dbal"
    commit: str = "acb68b388b2577bb211bb26dc22d20a8ad93d97d"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y wget git build-essential unzip libgd-dev libzip-dev libgmp-dev libftp-dev libcurl4-openssl-dev libpq-dev libsqlite3-dev && \
    docker-php-ext-install pdo pdo_mysql pdo_pgsql pdo_sqlite mysqli gd zip gmp ftp curl pcntl && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sS https://getcomposer.org/installer | php -- --2.2 --install-dir=/usr/local/bin --filename=composer

RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN composer update
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        passed_pattern = re.compile(r"^\s*✔\s*(.+)$")
        failed_pattern = re.compile(r"^\s*✘\s*(.+)$")
        skipped_pattern = re.compile(r"^\s*↩\s*(.+)$")
        for line in log.split("\n"):
            for pattern, status in (
                (passed_pattern, TestStatus.PASSED.value),
                (failed_pattern, TestStatus.FAILED.value),
                (skipped_pattern, TestStatus.SKIPPED.value),
            ):
                match = pattern.match(line)
                if match:
                    test_name = match.group(1).strip()
                    test_status_map[test_name] = status
                    break
        return test_status_map


# Register all Rust profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, PhpProfile)
        and obj.__name__ != "PhpProfile"
    ):
        global_registry.register_profile(obj)
