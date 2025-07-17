import docker
import re
from dataclasses import dataclass, field

from pathlib import Path
from swebench.harness.constants import (
    FAIL_TO_PASS,
    PASS_TO_PASS,
    KEY_INSTANCE_ID,
    TestStatus,
)
from swebench.harness.docker_build import build_image as build_image_sweb
from swebench.harness.dockerfiles import get_dockerfile_env
from swesmith.constants import LOG_DIR_ENV, ENV_NAME, INSTANCE_REF
from swesmith.profiles.base import RepoProfile, global_registry
from swesmith.profiles.utils import INSTALL_BAZEL, INSTALL_CMAKE


@dataclass
class PythonProfile(RepoProfile):
    """
    Profile for Python repositories.

    This class provides Python-specific defaults and functionality for
    repository profiles, including Python version management and common
    Python installation/test patterns.
    """

    python_version: str = "3.10"
    install_cmds: list[str] = field(
        default_factory=lambda: ["python -m pip install -e ."]
    )
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest --disable-warnings --color=no --tb=no --verbose"
    )
    exts: list[str] = field(default_factory=lambda: [".py"])

    def get_test_files(self, instance: dict) -> tuple[list[str], list[str]]:
        assert FAIL_TO_PASS in instance and PASS_TO_PASS in instance, (
            f"Instance {instance[KEY_INSTANCE_ID]} missing required keys {FAIL_TO_PASS} or {PASS_TO_PASS}"
        )
        _helper = lambda tests: sorted(list(set([x.split("::", 1)[0] for x in tests])))
        return _helper(instance[FAIL_TO_PASS]), _helper(instance[PASS_TO_PASS])

    def build_image(self):
        BASE_IMAGE_KEY = "jyangballin/swesmith.x86_64"
        HEREDOC_DELIMITER = "EOF_59812759871"
        PATH_TO_REQS = "swesmith_environment.yml"

        client = docker.from_env()
        with open(self._env_yml) as f:
            reqs = f.read()

        setup_commands = [
            "#!/bin/bash",
            "set -euxo pipefail",
            f"git clone -o origin https://github.com/{self.mirror_name} /{ENV_NAME}",
            f"cd /{ENV_NAME}",
            "source /opt/miniconda3/bin/activate",
            f"cat <<'{HEREDOC_DELIMITER}' > {PATH_TO_REQS}\n{reqs}\n{HEREDOC_DELIMITER}",
            f"conda env create --file {PATH_TO_REQS}",
            f"conda activate {ENV_NAME} && conda install python={self.python_version} -y",
            f"rm {PATH_TO_REQS}",
            f"conda activate {ENV_NAME}",
            'echo "Current environment: $CONDA_DEFAULT_ENV"',
        ] + self.install_cmds
        dockerfile = get_dockerfile_env(
            self.pltf, self.arch, "py", base_image_key=BASE_IMAGE_KEY
        )

        build_image_sweb(
            image_name=self.image_name,
            setup_scripts={"setup_env.sh": "\n".join(setup_commands) + "\n"},
            dockerfile=dockerfile,
            platform=self.pltf,
            client=client,
            build_dir=LOG_DIR_ENV / self.repo_name,
        )

    def log_parser(self, log: str) -> dict[str, str]:
        """Parser for test logs generated with PyTest framework"""
        test_status_map = {}
        for line in log.split("\n"):
            for status in TestStatus:
                is_match = re.match(rf"^(\S+)(\s+){status.value}", line)
                if is_match:
                    test_status_map[is_match.group(1)] = status.value
                    continue
        return test_status_map

    @property
    def _env_yml(self) -> Path:
        return LOG_DIR_ENV / self.repo_name / f"sweenv_{self.repo_name}.yml"


### MARK: Repository Profile Classes ###


@dataclass
class Addict75284f95(PythonProfile):
    owner: str = "mewwts"
    repo: str = "addict"
    commit: str = "75284f9593dfb929cadd900aff9e35e7c7aec54b"


@dataclass
class AliveProgress35853799(PythonProfile):
    owner: str = "rsalmei"
    repo: str = "alive-progress"
    commit: str = "35853799b84ee682af121f7bc5967bd9b62e34c4"


@dataclass
class Apispec8b421526(PythonProfile):
    owner: str = "marshmallow-code"
    repo: str = "apispec"
    commit: str = "8b421526ea1015046de42599dd93da6a3473fe44"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[dev]"])


@dataclass
class Arrow1d70d009(PythonProfile):
    owner: str = "arrow-py"
    repo: str = "arrow"
    commit: str = "1d70d0091980ea489a64fa95a48e99b45f29f0e7"


@dataclass
class AstroidB114f6b5(PythonProfile):
    owner: str = "pylint-dev"
    repo: str = "astroid"
    commit: str = "b114f6b58e749b8ab47f80490dce73ea80d8015f"


@dataclass
class AsyncTimeoutD0baa9f1(PythonProfile):
    owner: str = "aio-libs"
    repo: str = "async-timeout"
    commit: str = "d0baa9f162b866e91881ae6cfa4d68839de96fb5"


@dataclass
class AutogradAc044f0d(PythonProfile):
    owner: str = "HIPS"
    repo: str = "autograd"
    commit: str = "ac044f0de1185b725955595840135e9ade06aaed"
    install_cmds: list = field(
        default_factory=lambda: ["pip install -e '.[scipy,test]'"]
    )

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            for status in TestStatus:
                is_match = re.match(rf"^\[gw\d\]\s{status.value}\s(\S+)", line)
                if is_match:
                    test_status_map[is_match.group(1)] = status.value
                    continue
        return test_status_map


@dataclass
class Bleach73871d76(PythonProfile):
    owner: str = "mozilla"
    repo: str = "bleach"
    commit: str = "73871d766de1e33a296eeb4f9faf2451f28bee39"


@dataclass
class Boltons3bfcfdd0(PythonProfile):
    owner: str = "mahmoud"
    repo: str = "boltons"
    commit: str = "3bfcfdd04395b6cc74a5c0cdc72c8f64cc4ac01f"


@dataclass
class Bottlea8dfef30(PythonProfile):
    owner: str = "bottlepy"
    repo: str = "bottle"
    commit: str = "a8dfef301dec35f13e7578306002c40796651629"


@dataclass
class Cantools0c6a7871(PythonProfile):
    owner: str = "cantools"
    repo: str = "cantools"
    commit: str = "0c6a78711409e4307de34582f795ddb426d58dd8"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[dev,plot]"])


@dataclass
class ChannelsA144b4b8(PythonProfile):
    owner: str = "django"
    repo: str = "channels"
    commit: str = "a144b4b8881a93faa567a6bdf2d7f518f4c16cd2"
    install_cmds: list = field(
        default_factory=lambda: ["pip install -e .[tests,daphne]"]
    )


@dataclass
class Chardet9630f238(PythonProfile):
    owner: str = "chardet"
    repo: str = "chardet"
    commit: str = "9630f2382faa50b81be2f96fd3dfab5f6739a0ef"


@dataclass
class CharsetNormalizer1fdd6463(PythonProfile):
    owner: str = "jawah"
    repo: str = "charset_normalizer"
    commit: str = "1fdd64633572040ab60e62e8b24f29cb7e17660b"


@dataclass
class ClickFde47b4b4(PythonProfile):
    owner: str = "pallets"
    repo: str = "click"
    commit: str = "fde47b4b4f978f179b9dff34583cb2b99021f482"


@dataclass
class Cloudpickle6220b0ce(PythonProfile):
    owner: str = "cloudpipe"
    repo: str = "cloudpickle"
    commit: str = "6220b0ce83ffee5e47e06770a1ee38ca9e47c850"


@dataclass
class PythonColorlogDfa10f59(PythonProfile):
    owner: str = "borntyping"
    repo: str = "python-colorlog"
    commit: str = "dfa10f59186d3d716aec4165ee79e58f2265c0eb"


@dataclass
class CookiecutterB4451231(PythonProfile):
    owner: str = "cookiecutter"
    repo: str = "cookiecutter"
    commit: str = "b4451231809fb9e4fc2a1e95d433cb030e4b9e06"


@dataclass
class Daphne32ac73e1(PythonProfile):
    owner: str = "django"
    repo: str = "daphne"
    commit: str = "32ac73e1a0fb87af0e3280c89fe4cc3ff1231b37"


@dataclass
class Dataset5c2dc8d3(PythonProfile):
    owner: str = "pudo"
    repo: str = "dataset"
    commit: str = "5c2dc8d3af1e0af0290dcd7ae2cae92589f305a1"
    install_cmds: list = field(default_factory=lambda: ["python setup.py install"])


@dataclass
class DeepdiffEd252022(PythonProfile):
    owner: str = "seperman"
    repo: str = "deepdiff"
    commit: str = "ed2520229d0369813f6e54cdf9c7e68e8073ef62"
    install_cmds: list = field(
        default_factory=lambda: [
            "pip install -r requirements-dev.txt",
            "pip install -e .",
        ]
    )


@dataclass
class DjangoMoney835c1ab8(PythonProfile):
    owner: str = "django-money"
    repo: str = "django-money"
    commit: str = "835c1ab867d11137b964b94936692bea67a038ec"
    install_cmds: list = field(
        default_factory=lambda: ["pip install -e .[test,exchange]"]
    )


@dataclass
class Dominate9082227e(PythonProfile):
    owner: str = "Knio"
    repo: str = "dominate"
    commit: str = "9082227e93f5a370012bb934286caf7385d3e7ac"


@dataclass
class PythonDotenv2b8635b7(PythonProfile):
    owner: str = "theskumar"
    repo: str = "python-dotenv"
    commit: str = "2b8635b79f1aa15cade0950117d4e7d12c298766"


@dataclass
class DrfNestedRouters6144169d(PythonProfile):
    owner: str = "alanjds"
    repo: str = "drf-nested-routers"
    commit: str = "6144169d5c33a1c5134b2fedac1d6cfa312c174e"
    install_cmds: list = field(
        default_factory=lambda: ["pip install -r requirements.txt", "pip install -e ."]
    )


@dataclass
class Environs73c372df(PythonProfile):
    owner: str = "sloria"
    repo: str = "environs"
    commit: str = "73c372df71002312615ad0349ae11274bb3edc69"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[dev]"])


@dataclass
class Exceptiongroup0b4f4937(PythonProfile):
    owner: str = "agronholm"
    repo: str = "exceptiongroup"
    commit: str = "0b4f49378b585a338ae10abd72ec2006c5057d7b"


@dataclass
class Faker8b401a7d(PythonProfile):
    owner: str = "joke2k"
    repo: str = "faker"
    commit: str = "8b401a7d68f5fda1276f36a8fc502ef32050ed72"


@dataclass
class FeedparserCad965a3(PythonProfile):
    owner: str = "kurtmckee"
    repo: str = "feedparser"
    commit: str = "cad965a3f52c4b077221a2142fb14ef7f68cd576"


@dataclass
class Flake8Cf1542ce(PythonProfile):
    owner: str = "PyCQA"
    repo: str = "flake8"
    commit: str = "cf1542cefa3e766670b2066dd75c4571d682a649"


@dataclass
class FlashtextB316c7e9(PythonProfile):
    owner: str = "vi3k6i5"
    repo: str = "flashtext"
    commit: str = "b316c7e9e54b6b4d078462b302a83db85f884a94"


@dataclass
class FlaskBc098406(PythonProfile):
    owner: str = "pallets"
    repo: str = "flask"
    commit: str = "bc098406af9537aacc436cb2ea777fbc9ff4c5aa"


@dataclass
class Freezegun5f171db0(PythonProfile):
    owner: str = "spulec"
    repo: str = "freezegun"
    commit: str = "5f171db0aaa02c4ade003bbc8885e0bb19efbc81"


@dataclass
class Funcy207a7810(PythonProfile):
    owner: str = "Suor"
    repo: str = "funcy"
    commit: str = "207a7810c216c7408596d463d3f429686e83b871"


@dataclass
class FurlDa386f68(PythonProfile):
    owner: str = "gruns"
    repo: str = "furl"
    commit: str = "da386f68b8d077086c25adfd205a4c3d502c3012"


@dataclass
class FvcoreA491d5b9(PythonProfile):
    owner: str = "facebookresearch"
    repo: str = "fvcore"
    commit: str = "a491d5b9a06746f387aca2f1f9c7c7f28e20bef9"
    install_cmds: list = field(
        default_factory=lambda: [
            "pip install torch shapely",
            "rm tests/test_focal_loss.py",
            "pip install -e .",
        ]
    )


@dataclass
class GlomFb3c4e76(PythonProfile):
    owner: str = "mahmoud"
    repo: str = "glom"
    commit: str = "fb3c4e76f28816aebfd2538980e617742e98a7c2"


@dataclass
class Gpxpy09fc46b3(PythonProfile):
    owner: str = "tkrajina"
    repo: str = "gpxpy"
    commit: str = "09fc46b3cad16b5bf49edf8e7ae873794a959620"
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest test.py --verbose --color=no --tb=no --disable-warnings"
    )


@dataclass
class Grafanalib5c3b17ed(PythonProfile):
    owner: str = "weaveworks"
    repo: str = "grafanalib"
    commit: str = "5c3b17edaa437f0bc09b5f1b9275dc8fb91689fb"


@dataclass
class Graphene82903263(PythonProfile):
    owner: str = "graphql-python"
    repo: str = "graphene"
    commit: str = "82903263080b3b7f22c2ad84319584d7a3b1a1f6"


@dataclass
class GspreadA8be3b96(PythonProfile):
    owner: str = "burnash"
    repo: str = "gspread"
    commit: str = "a8be3b96f9276779ab680d84a0982282fb184000"


@dataclass
class GTTSDbcda4f39(PythonProfile):
    owner: str = "pndurette"
    repo: str = "gTTS"
    commit: str = "dbcda4f396074427172d4a1f798a172686ace6e0"


@dataclass
class GunicornBacbf8aa(PythonProfile):
    owner: str = "benoitc"
    repo: str = "gunicorn"
    commit: str = "bacbf8aa5152b94e44aa5d2a94aeaf0318a85248"


@dataclass
class H11Bed0dd4ae(PythonProfile):
    owner: str = "python-hyper"
    repo: str = "h11"
    commit: str = "bed0dd4ae9774b962b19833941bb9ec4dc403da9"


@dataclass
class IcecreamF76fef56(PythonProfile):
    owner: str = "gruns"
    repo: str = "icecream"
    commit: str = "f76fef56b66b59fd9a89502c60a99fbe28ee36bd"


@dataclass
class InflectC079a96a(PythonProfile):
    owner: str = "jaraco"
    repo: str = "inflect"
    commit: str = "c079a96a573ece60b54bd5210bb0f414beb74dcd"


@dataclass
class Iniconfig16793ead(PythonProfile):
    owner: str = "pytest-dev"
    repo: str = "iniconfig"
    commit: str = "16793eaddac67de0b8d621ae4e42e05b927e8d67"


@dataclass
class Isodate17cb25eb(PythonProfile):
    owner: str = "gweis"
    repo: str = "isodate"
    commit: str = "17cb25eb7bc3556a68f3f7b241313e9bb8b23760"


@dataclass
class JaxEbd90e06f(PythonProfile):
    owner: str = "jax-ml"
    repo: str = "jax"
    commit: str = "ebd90e06fa7caad087e2342431e3899cfd2fdf98"
    install_cmds: list = field(default_factory=lambda: ['pip install -e ".[cpu]"'])
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest --disable-warnings --color=no --tb=no --verbose -n auto"
    )
    min_testing: bool = True
    min_pregold: bool = True


@dataclass
class JinjaAda0a9a6(PythonProfile):
    owner: str = "pallets"
    repo: str = "jinja"
    commit: str = "ada0a9a6fc265128b46949b5144d2eaa55e6df2c"


@dataclass
class Jsonschema93e0caa5(PythonProfile):
    owner: str = "python-jsonschema"
    repo: str = "jsonschema"
    commit: str = "93e0caa5752947ec77333da81a634afe41a022ed"


@dataclass
class LangdetectA1598f1a(PythonProfile):
    owner: str = "Mimino666"
    repo: str = "langdetect"
    commit: str = "a1598f1afcbfe9a758cfd06bd688fbc5780177b2"


@dataclass
class LineProfilerA646bf0f(PythonProfile):
    owner: str = "pyutils"
    repo: str = "line_profiler"
    commit: str = "a646bf0f9ab3d15264a1be14d0d4ee6894966f6a"


@dataclass
class PythonMarkdownify6258f5c3(PythonProfile):
    owner: str = "matthewwithanm"
    repo: str = "python-markdownify"
    commit: str = "6258f5c38b97ab443b4ddf03e6676ce29b392d06"


@dataclass
class Markupsafe620c06c9(PythonProfile):
    owner: str = "pallets"
    repo: str = "markupsafe"
    commit: str = "620c06c919c1bd7bb1ce3dbee402e1c0c56e7ac3"


@dataclass
class Marshmallow9716fc62(PythonProfile):
    owner: str = "marshmallow-code"
    repo: str = "marshmallow"
    commit: str = "9716fc629976c9d3ce30cd15d270d9ac235eb725"


@dataclass
class MidoA0158ff9(PythonProfile):
    owner: str = "mido"
    repo: str = "mido"
    commit: str = "a0158ff95a08f9a4eef628a2e7c793fd3a466640"
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest --disable-warnings --color=no --tb=no --verbose -rs -c /dev/null"
    )

    def get_test_files(self, instance: dict) -> list[str]:
        f2p_files, p2p_files = super().get_test_files(instance)
        prefix = "../dev/"
        _helper = (
            lambda test_file: test_file[len(prefix) :]
            if test_file.startswith(prefix)
            else test_file
        )
        remove_prefix = lambda test_files: sorted(list(set(map(_helper, test_files))))
        return remove_prefix(f2p_files), remove_prefix(p2p_files)


@dataclass
class MistuneBf54ef67(PythonProfile):
    owner: str = "lepture"
    repo: str = "mistune"
    commit: str = "bf54ef67390e02a5cdee7495d4386d7770c1902b"


@dataclass
class Nikola0f4c230e(PythonProfile):
    owner: str = "getnikola"
    repo: str = "nikola"
    commit: str = "0f4c230e5159e4e937463eb8d6d2ddfcbb09def2"
    install_cmds: list = field(
        default_factory=lambda: ["pip install -e '.[extras,tests]'"]
    )


@dataclass
class Oauthlib1fd52536(PythonProfile):
    owner: str = "oauthlib"
    repo: str = "oauthlib"
    commit: str = "1fd5253630c03e3f12719dd8c13d43111f66a8d2"


@dataclass
class Paramiko23f92003(PythonProfile):
    owner: str = "paramiko"
    repo: str = "paramiko"
    commit: str = "23f92003898b060df0e2b8b1d889455264e63a3e"
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest -rA --color=no --disable-warnings"
    )

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            for status in TestStatus:
                is_match = re.match(rf"^{status.value}\s(\S+)", line)
                if is_match:
                    test_status_map[is_match.group(1)] = status.value
                    continue
        return test_status_map


@dataclass
class Parse30da9e4f(PythonProfile):
    owner: str = "r1chardj0n3s"
    repo: str = "parse"
    commit: str = "30da9e4f37fdd979487c9fe2673df35b6b204c72"


@dataclass
class Parsimonious0d3f5f93(PythonProfile):
    owner: str = "erikrose"
    repo: str = "parsimonious"
    commit: str = "0d3f5f93c98ae55707f0958366900275d1ce094f"


@dataclass
class Parso338a5760(PythonProfile):
    owner: str = "davidhalter"
    repo: str = "parso"
    commit: str = "338a57602740ad0645b2881e8c105ffdc959e90d"
    install_cmds: list = field(default_factory=lambda: ["python setup.py install"])


@dataclass
class PatsyA5d16484(PythonProfile):
    owner: str = "pydata"
    repo: str = "patsy"
    commit: str = "a5d1648401b0ea0649b077f4b98da27db947d2d0"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[test]"])


@dataclass
class PdfminerSix1a8bd2f7(PythonProfile):
    owner: str = "pdfminer"
    repo: str = "pdfminer.six"
    commit: str = "1a8bd2f730295b31d6165e4d95fcb5a03793c978"


@dataclass
class Pdfplumber02ff4313(PythonProfile):
    owner: str = "jsvine"
    repo: str = "pdfplumber"
    commit: str = "02ff4313f846380fefccec9c73fb4c8d8a80d0ee"
    install_cmds: list = field(
        default_factory=lambda: [
            "apt-get update && apt-get install ghostscript -y",
            "pip install -e .",
        ]
    )


@dataclass
class PipdeptreeC31b6418(PythonProfile):
    owner: str = "tox-dev"
    repo: str = "pipdeptree"
    commit: str = "c31b641817f8235df97adf178ffd8e4426585f7a"
    install_cmds: list = field(
        default_factory=lambda: [
            "apt-get update && apt-get install graphviz -y",
            "pip install -e .[test,graphviz]",
        ]
    )


@dataclass
class PrettytableCa90b055(PythonProfile):
    owner: str = "prettytable"
    repo: str = "prettytable"
    commit: str = "ca90b055f20a6e8a06dcc46c2e3afe8ff1e8d0f1"


@dataclass
class Ptyprocess1067dbda(PythonProfile):
    owner: str = "pexpect"
    repo: str = "ptyprocess"
    commit: str = "1067dbdaf5cc3ab4786ae355aba7b9512a798734"


@dataclass
class Pyasn10f07d724(PythonProfile):
    owner: str = "pyasn1"
    repo: str = "pyasn1"
    commit: str = "0f07d7242a78ab4d129b26256d7474f7168cf536"


@dataclass
class Pydicom7d361b3d(PythonProfile):
    owner: str = "pydicom"
    repo: str = "pydicom"
    commit: str = "7d361b3d764dbbb1f8ad7af015e80ce96f6bf286"
    python_version: str = "3.11"


@dataclass
class PyfigletF8c5f35b(PythonProfile):
    owner: str = "pwaller"
    repo: str = "pyfiglet"
    commit: str = "f8c5f35be70a4bbf93ac032334311b326bc61688"


@dataclass
class Pygments27649ebbf(PythonProfile):
    owner: str = "pygments"
    repo: str = "pygments"
    commit: str = "27649ebbf5a2519725036b48ec99ef7745f100af"


@dataclass
class Pyopenssl04766a49(PythonProfile):
    owner: str = "pyca"
    repo: str = "pyopenssl"
    commit: str = "04766a496eb11f69f6226a5a0dfca4db90a5cbd1"


@dataclass
class Pyparsing533adf47(PythonProfile):
    owner: str = "pyparsing"
    repo: str = "pyparsing"
    commit: str = "533adf471f85b570006871e60a2e585fcda5b085"


@dataclass
class Pypika1c9646f0(PythonProfile):
    owner: str = "kayak"
    repo: str = "pypika"
    commit: str = "1c9646f0a019a167c32b649b6f5e6423c5ba2c9b"


@dataclass
class Pyquery811cd048(PythonProfile):
    owner: str = "gawel"
    repo: str = "pyquery"
    commit: str = "811cd048ffbe4e69fdc512863671131f98d691fb"


@dataclass
class PySnooper57472b46(PythonProfile):
    owner: str = "cool-RR"
    repo: str = "PySnooper"
    commit: str = "57472b4677b6c041647950f28f2d5750c38326c6"


@dataclass
class PythonDocx0cf6d71f(PythonProfile):
    owner: str = "python-openxml"
    repo: str = "python-docx"
    commit: str = "0cf6d71fb47ede07ecd5de2a8655f9f46c5f083d"


@dataclass
class PythonJsonLogger5f85723f(PythonProfile):
    owner: str = "madzak"
    repo: str = "python-json-logger"
    commit: str = "5f85723f4693c7289724fdcda84cfc0b62da74d4"


@dataclass
class PythonPinyinE42dede5(PythonProfile):
    owner: str = "mozillazg"
    repo: str = "python-pinyin"
    commit: str = "e42dede51abbc40e225da9a8ec8e5bd0043eed21"


@dataclass
class PythonPptx278b47b1(PythonProfile):
    owner: str = "scanny"
    repo: str = "python-pptx"
    commit: str = "278b47b1dedd5b46ee84c286e77cdfb0bf4594be"


@dataclass
class PythonQrcode456b01d4(PythonProfile):
    owner: str = "lincolnloop"
    repo: str = "python-qrcode"
    commit: str = "456b01d41f16e0cfb0f70c687848e276b78c3e8a"


@dataclass
class PythonReadability40256f40(PythonProfile):
    owner: str = "buriy"
    repo: str = "python-readability"
    commit: str = "40256f40389c1f97be5e83d7838547581653c6aa"


@dataclass
class PythonSlugify872b3750(PythonProfile):
    owner: str = "un33k"
    repo: str = "python-slugify"
    commit: str = "872b37509399a7f02e53f46ad9881f63f66d334b"
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "python test.py --verbose"
    )

    def get_test_files(self, instance: dict) -> list[str]:
        return ["test.py"], ["test.py"]

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        pattern = r"^([a-zA-Z0-9_\-,\.\s\(\)']+)\s\.{3}\s"
        for line in log.split("\n"):
            is_match = re.match(f"{pattern}ok$", line)
            if is_match:
                test_status_map[is_match.group(1)] = TestStatus.PASSED.value
                continue
            for keyword, status in {
                "FAIL": TestStatus.FAILED,
                "ERROR": TestStatus.ERROR,
            }.items():
                is_match = re.match(f"{pattern}{keyword}$", line)
                if is_match:
                    test_status_map[is_match.group(1)] = status.value
                    continue
        return test_status_map


@dataclass
class Radon54b88e58(PythonProfile):
    owner: str = "rubik"
    repo: str = "radon"
    commit: str = "54b88e5878b2724bf4d77f97349588b811abdff2"


@dataclass
class Records5941ab27(PythonProfile):
    owner: str = "kennethreitz"
    repo: str = "records"
    commit: str = "5941ab2798cb91455b6424a9564c9cd680475fbe"


@dataclass
class RedDiscordBot33e0eac7(PythonProfile):
    owner: str = "Cog-Creators"
    repo: str = "Red-DiscordBot"
    commit: str = "33e0eac741955ce5b7e89d9b8f2f2712727af770"


@dataclass
class Result0b855e1e(PythonProfile):
    owner: str = "rustedpy"
    repo: str = "result"
    commit: str = "0b855e1e38a08d6f0a4b0138b10c127c01e54ab4"


@dataclass
class Safety7654596b(PythonProfile):
    owner: str = "pyupio"
    repo: str = "safety"
    commit: str = "7654596be933f8310b294dbc85a7af6066d06e4f"


@dataclass
class Scrapy35212ec5(PythonProfile):
    owner: str = "scrapy"
    repo: str = "scrapy"
    commit: str = "35212ec5b05a3af14c9f87a6193ab24e33d62f9f"
    install_cmds: list = field(
        default_factory=lambda: [
            "apt-get update && apt-get install -y libxml2-dev libxslt-dev libjpeg-dev",
            "python -m pip install -e .",
            "rm tests/test_feedexport.py",
            "rm tests/test_pipeline_files.py",
        ]
    )
    min_testing: bool = True


@dataclass
class Schedule82a43db1(PythonProfile):
    owner: str = "dbader"
    repo: str = "schedule"
    commit: str = "82a43db1b938d8fdf60103bd41f329e06c8d3651"


@dataclass
class Schema24a30457(PythonProfile):
    owner: str = "keleshev"
    repo: str = "schema"
    commit: str = "24a3045773eac497c659f24b32f24a281be9f286"


@dataclass
class SoupsieveA8080d97(PythonProfile):
    owner: str = "facelessuser"
    repo: str = "soupsieve"
    commit: str = "a8080d97a0355e316981cb0c5c887a861c4244e3"


@dataclass
class Sqlfluff50a1c4b6(PythonProfile):
    owner: str = "sqlfluff"
    repo: str = "sqlfluff"
    commit: str = "50a1c4b6ff171188b6b70b39afe82a707b4919ac"
    min_testing: bool = True


@dataclass
class Sqlglot036601ba(PythonProfile):
    owner: str = "tobymao"
    repo: str = "sqlglot"
    commit: str = "036601ba9cbe4d175d6a9d38bc27587eab858968"
    install_cmds: list = field(default_factory=lambda: ['pip install -e ".[dev]"'])
    min_testing: bool = True


@dataclass
class SqlparseE57923b3(PythonProfile):
    owner: str = "andialbrecht"
    repo: str = "sqlparse"
    commit: str = "e57923b3aa823c524c807953cecc48cf6eec2cb2"


@dataclass
class Stackprinter219fcc52(PythonProfile):
    owner: str = "cknd"
    repo: str = "stackprinter"
    commit: str = "219fcc522fa5fd6e440703358f6eb408f3ffc007"


@dataclass
class StarletteDb5063c2(PythonProfile):
    owner: str = "encode"
    repo: str = "starlette"
    commit: str = "db5063c26030e019f7ee62aef9a1b564eca9f1d6"


@dataclass
class PythonStringSimilarity115acaac(PythonProfile):
    owner: str = "luozhouyang"
    repo: str = "python-string-similarity"
    commit: str = "115acaacf926b41a15664bd34e763d074682bda3"


@dataclass
class SunpyF8edfd5c(PythonProfile):
    owner: str = "sunpy"
    repo: str = "sunpy"
    commit: str = "f8edfd5c4be873fbd28dec4583e7f737a045f546"
    python_version: str = "3.11"
    install_cmds: list = field(default_factory=lambda: ['pip install -e ".[dev]"'])
    min_testing: bool = True


@dataclass
class Dspy651a4c71(PythonProfile):
    owner: str = "stanfordnlp"
    repo: str = "dspy"
    commit: str = "651a4c715ecc6c5e68b68d22172768f0b20f2eea"


@dataclass
class Sympy2ab64612(PythonProfile):
    owner: str = "sympy"
    repo: str = "sympy"
    commit: str = "2ab64612efb287f09822419f4127878a4b664f71"
    min_testing: bool = True
    min_pregold: bool = True


@dataclass
class Tenacity0d40e76f(PythonProfile):
    owner: str = "jd"
    repo: str = "tenacity"
    commit: str = "0d40e76f7d06d631fb127e1ec58c8bd776e70d49"


@dataclass
class Termcolor3a42086f(PythonProfile):
    owner: str = "termcolor"
    repo: str = "termcolor"
    commit: str = "3a42086feb35647bc5aa5f1065b0327200da6b9b"


@dataclass
class TextdistanceC3aca916(PythonProfile):
    owner: str = "life4"
    repo: str = "textdistance"
    commit: str = "c3aca916bd756a8cb71114688b469ec90ef5b232"
    install_cmds: list = field(
        default_factory=lambda: ['pip install -e ".[benchmark,test]"']
    )


@dataclass
class TextfsmC31b6007(PythonProfile):
    owner: str = "google"
    repo: str = "textfsm"
    commit: str = "c31b600743895f018e7583f93405a3738a9f4d55"


@dataclass
class Thefuzz8a05a3ee(PythonProfile):
    owner: str = "seatgeek"
    repo: str = "thefuzz"
    commit: str = "8a05a3ee38cbd00a2d2f4bb31db34693b37a1fdd"


@dataclass
class Tinydb10644a0e(PythonProfile):
    owner: str = "msiemens"
    repo: str = "tinydb"
    commit: str = "10644a0e07ad180c5b756aba272ee6b0dbd12df8"


@dataclass
class Tldextract3d1bf184(PythonProfile):
    owner: str = "john-kurkowski"
    repo: str = "tldextract"
    commit: str = "3d1bf184d4f20fbdbadd6274560ccd438939160e"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[testing]"])


@dataclass
class Tomli443a0c1b(PythonProfile):
    owner: str = "hukkin"
    repo: str = "tomli"
    commit: str = "443a0c1bc5da39b7ed84306912ee1900e6b72e2f"


@dataclass
class TornadoD5ac65c1(PythonProfile):
    owner: str = "tornadoweb"
    repo: str = "tornado"
    commit: str = "d5ac65c1f1453c2aeddd089d8e68c159645c13e1"
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "python -m tornado.test --verbose"
    )

    def get_test_files(self, instance: dict) -> list[str]:
        f2p_files = set()
        p2p_files = set()
        for i, j in (
            (PASS_TO_PASS, p2p_files),
            (FAIL_TO_PASS, f2p_files),
        ):
            for test_name in instance[i]:
                is_match = re.search(r"\s\((.*)\)", test_name)
                if is_match:
                    test_path = is_match.group(1)
                    j.add("/".join(test_path.split(".")[:-1]) + ".py")
        return list(f2p_files), list(p2p_files)

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            if line.endswith("... ok"):
                test_case = line.split(" ... ")[0]
                test_status_map[test_case] = TestStatus.PASSED.value
            elif " ... skipped " in line:
                test_case = line.split(" ... ")[0]
                test_status_map[test_case] = TestStatus.SKIPPED.value
            elif any([line.startswith(x) for x in ["ERROR:", "FAIL:"]]):
                test_case = " ".join(line.split()[1:3])
                test_status_map[test_case] = TestStatus.FAILED.value
        return test_status_map


@dataclass
class TrioCfbbe2c1(PythonProfile):
    owner: str = "python-trio"
    repo: str = "trio"
    commit: str = "cfbbe2c1f96e93b19bc2577d2cab3f4fe2e81153"


@dataclass
class Tweepy91a41c6e(PythonProfile):
    owner: str = "tweepy"
    repo: str = "tweepy"
    commit: str = "91a41c6e1c955d278c370d51d5cf43b05f7cd979"
    install_cmds: list = field(
        default_factory=lambda: ["pip install -e '.[dev,test,async]'"]
    )


@dataclass
class TypeguardB6a7e438(PythonProfile):
    owner: str = "agronholm"
    repo: str = "typeguard"
    commit: str = "b6a7e4387c30a9f7d635712157c889eb073c1ea3"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[test,doc]"])


@dataclass
class UsaddressA42a8f0c(PythonProfile):
    owner: str = "datamade"
    repo: str = "usaddress"
    commit: str = "a42a8f0c14bd2e273939fd51c604f10826301e73"
    install_cmds: list = field(default_factory=lambda: ["pip install -e .[dev]"])


@dataclass
class VoluptuousA7a55f83(PythonProfile):
    owner: str = "alecthomas"
    repo: str = "voluptuous"
    commit: str = "a7a55f83b9fa7ba68b0669b3d78a61de703e0a16"


@dataclass
class WebargsDbde72fe(PythonProfile):
    owner: str = "marshmallow-code"
    repo: str = "webargs"
    commit: str = "dbde72fe5db8a999acd1716d5ef855ab7cc1a274"


@dataclass
class WordCloudEc24191c(PythonProfile):
    owner: str = "amueller"
    repo: str = "word_cloud"
    commit: str = "ec24191c64570d287032c5a4179c38237cd94043"


@dataclass
class Xmltodict0952f382(PythonProfile):
    owner: str = "martinblech"
    repo: str = "xmltodict"
    commit: str = "0952f382c2340bc8b86a5503ba765a35a49cf7c4"


@dataclass
class Yamllint8513d9b9(PythonProfile):
    owner: str = "adrienverge"
    repo: str = "yamllint"
    commit: str = "8513d9b97da3b32453b3fccb221f4ab134a028d7"


@dataclass
class Moto694ce1f4(PythonProfile):
    owner: str = "getmoto"
    repo: str = "moto"
    commit: str = "694ce1f4880c784fed0553bc19b2ace6691bc109"
    python_version = "3.12"
    install_cmds: list = field(default_factory=lambda: ["make init"])
    min_testing: bool = True


@dataclass
class MypyE93f06ce(PythonProfile):
    owner: str = "python"
    repo: str = "mypy"
    commit: str = "e93f06ceab81d8ff1f777c7587d04c339cfd5a16"
    python_version = "3.12"
    install_cmds: list = field(
        default_factory=lambda: [
            "git submodule update --init mypy/typeshed || true",
            "python -m pip install -r test-requirements.txt",
            "python -m pip install -e .",
            "hash -r",
        ]
    )
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest --color=no -rA -k"
    )
    min_testing: bool = True

    def get_test_cmd(self, instance: str, f2p_only: bool = False) -> tuple[str, list]:
        test_keys = []
        if f2p_only and FAIL_TO_PASS in instance:
            test_keys = [x.rsplit("::", 1)[-1] for x in instance[FAIL_TO_PASS]]
        elif INSTANCE_REF in instance and "test_patch" in instance[INSTANCE_REF]:
            test_keys = re.findall(
                r"\[case ([^\]]+)\]", instance[INSTANCE_REF]["test_patch"]
            )
        if len(test_keys) > 1:
            combined = " or ".join(test_keys)
            return f'{self.test_cmd} "{combined}"', test_keys
        return self.test_cmd, test_keys

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            for status in [
                TestStatus.PASSED.value,
                TestStatus.FAILED.value,
            ]:
                if status in line:
                    test_case = line.split()[-1]
                    test_status_map[test_case] = status
                    break
        return test_status_map


@dataclass
class MONAIa09c1f08(PythonProfile):
    owner: str = "Project-MONAI"
    repo: str = "MONAI"
    commit: str = "a09c1f08461cec3d2131fde3939ef38c3c4ad5fc"
    python_version = "3.12"
    install_cmds: list = field(
        default_factory=lambda: [
            r"sed -i '/^git+https:\/\/github.com\/Project-MONAI\//d' requirements-dev.txt",
            "python -m pip install -U -r requirements-dev.txt",
            "python -m pip install -e .",
        ]
    )
    test_cmd: str = (
        "source /opt/miniconda3/bin/activate; "
        f"conda activate {ENV_NAME}; "
        "pytest --disable-warnings --color=no --tb=no --verbose"
    )
    min_pregold: bool = True
    min_testing: bool = True


@dataclass
class Dvc1d6ea681(PythonProfile):
    owner: str = "iterative"
    repo: str = "dvc"
    commit: str = "1d6ea68133289ceab2637ce7095772678af792c6"
    install_cmds: list = field(default_factory=lambda: ['pip install -e ".[dev]"'])
    min_testing: bool = True


@dataclass
class Hydra0f03eb60(PythonProfile):
    owner: str = "facebookresearch"
    repo: str = "hydra"
    commit: str = "0f03eb60c2ecd1fbdb25ede9a2c4faeac81de491"
    install_cmds: list = field(
        default_factory=lambda: [
            "apt-get update && apt-get install -y openjdk-17-jdk openjdk-17-jre",
            "pip install -e .",
        ]
    )
    min_testing: bool = True


@dataclass
class Dask5f61e423(PythonProfile):
    owner: str = "dask"
    repo: str = "dask"
    commit: str = "5f61e42324c3a6cd4da17b5d5ebe4663aa4b8783"
    install_cmds: list = field(
        default_factory=lambda: [
            "python -m pip install graphviz",
            "python -m pip install -e .",
        ]
    )
    min_testing: bool = True


@dataclass
class Modin8c7799fd(PythonProfile):
    owner: str = "modin-project"
    repo: str = "modin"
    commit: str = "8c7799fdbbc2fb0543224160dd928215852b7757"
    install_cmds: list = field(default_factory=lambda: ['pip install -e ".[all]"'])
    min_pregold: bool = True
    min_testing: bool = True


@dataclass
class PydanticAcb0f10f(PythonProfile):
    owner: str = "pydantic"
    repo: str = "pydantic"
    commit: str = "acb0f10fda1c78441e052c57b4288bc91431f852"
    install_cmds: list = field(
        default_factory=lambda: [
            "apt-get update && apt-get install -y locales pipx",
            "pipx install uv",
            "pipx install pre-commit",
            'export PATH="$HOME/.local/bin:$PATH"',
            "make install",
        ]
    )
    test_cmd: str = (
        "/root/.local/bin/uv run pytest --disable-warnings --color=no --tb=no --verbose"
    )


@dataclass
class Conan86f29e13(PythonProfile):
    owner: str = "conan-io"
    repo: str = "conan"
    commit: str = "86f29e137a10bb6ed140c1a8c05c3099987b13c5"
    install_cmds = (
        INSTALL_CMAKE
        + INSTALL_BAZEL
        + [
            "apt-get -y update && apt-get -y upgrade && apt-get install -y build-essential cmake automake autoconf pkg-config meson ninja-build",
            "python -m pip install -r conans/requirements.txt",
            "python -m pip install -r conans/requirements_server.txt",
            "python -m pip install -r conans/requirements_dev.txt",
            "python -m pip install -e .",
        ]
    )
    min_testing: bool = True


@dataclass
class Pandas95280573(PythonProfile):
    owner: str = "pandas-dev"
    repo: str = "pandas"
    commit: str = "95280573e15be59036f98d82a8792599c10c6603"
    install_cmds: list = field(
        default_factory=lambda: [
            "git remote add upstream https://github.com/pandas-dev/pandas.git",
            "git fetch upstream --tags",
            "python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true",
            """sed -i 's/__version__="[^"]*"/__version__="3.0.0.dev0+1992.g95280573e1"/' build/cp310/_version_meson.py""",
        ]
    )
    min_pregold: bool = True
    min_testing: bool = True


@dataclass
class MonkeyType70c3acf6(PythonProfile):
    owner: str = "Instagram"
    repo: str = "MonkeyType"
    commit: str = "70c3acf62950be5dfb28743c7a719bfdecebcd84"


@dataclass
class String2Stringc4a72f59(PythonProfile):
    owner: str = "stanfordnlp"
    repo: str = "string2string"
    commit: str = "c4a72f59aafe8db42c4015709078064535dc4191"
    install_cmds: list = field(
        default_factory=lambda: [
            "pip install -r docs/requirements.txt",
            "pip install -e .",
            "pip install pytest",
        ]
    )


# Register all Python profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, PythonProfile)
        and obj.__name__ != "PythonProfile"
    ):
        global_registry.register_profile(obj)
