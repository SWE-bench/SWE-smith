import docker
import re

from pathlib import Path
from swebench.harness.constants import TestStatus
from swebench.harness.docker_build import build_image as build_image_sweb
from swebench.harness.dockerfiles import get_dockerfile_env
from swesmith.constants import LOG_DIR_ENV, ENV_NAME
from swesmith.profiles.base import RepoProfile, global_registry
from swesmith.profiles.utils import INSTALL_BAZEL, INSTALL_CMAKE
from swesmith.utils import get_arch_and_platform


class PythonProfile(RepoProfile):
    """
    Profile for Python repositories.

    This class provides Python-specific defaults and functionality for
    repository profiles, including Python version management and common
    Python installation/test patterns.
    """

    python_version: str = "3.10"
    install_cmds: list[str] = ["python -m pip install -e ."]
    test_cmd: str = "pytest --disable-warnings --color=no --tb=no --verbose"

    def build_image(self):
        BASE_IMAGE_KEY = "jyangballin/swesmith.x86_64"
        HEREDOC_DELIMITER = "EOF_59812759871"
        PATH_TO_REQS = "swesmith_environment.yml"

        client = docker.from_env()
        reqs = open(self._env_yml).read()

        arch, platform = get_arch_and_platform()
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
            platform, arch, "py", base_image_key=BASE_IMAGE_KEY
        )

        build_image_sweb(
            image_name=self.image_name,
            setup_scripts={"setup_env.sh": "\n".join(setup_commands) + "\n"},
            dockerfile=dockerfile,
            platform=platform,
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


class Addict75284f95(PythonProfile):
    owner = "mewwts"
    repo = "addict"
    commit = "75284f9593dfb929cadd900aff9e35e7c7aec54b"


class AliveProgress35853799(PythonProfile):
    owner = "rsalmei"
    repo = "alive-progress"
    commit = "35853799b84ee682af121f7bc5967bd9b62e34c4"


class Apispec8b421526(PythonProfile):
    owner = "marshmallow-code"
    repo = "apispec"
    commit = "8b421526ea1015046de42599dd93da6a3473fe44"
    install_cmds = ["pip install -e .[dev]"]


class Arrow1d70d009(PythonProfile):
    owner = "arrow-py"
    repo = "arrow"
    commit = "1d70d0091980ea489a64fa95a48e99b45f29f0e7"


class AstroidB114f6b5(PythonProfile):
    owner = "pylint-dev"
    repo = "astroid"
    commit = "b114f6b58e749b8ab47f80490dce73ea80d8015f"


class AsyncTimeoutD0baa9f1(PythonProfile):
    owner = "aio-libs"
    repo = "async-timeout"
    commit = "d0baa9f162b866e91881ae6cfa4d68839de96fb5"


class AutogradAc044f0d(PythonProfile):
    owner = "HIPS"
    repo = "autograd"
    commit = "ac044f0de1185b725955595840135e9ade06aaed"
    install_cmds = ["pip install -e '.[scipy,test]'"]

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            for status in TestStatus:
                is_match = re.match(rf"^\[gw\d\]\s{status.value}\s(\S+)", line)
                if is_match:
                    test_status_map[is_match.group(1)] = status.value
                    continue
        return test_status_map


class Bleach73871d76(PythonProfile):
    owner = "mozilla"
    repo = "bleach"
    commit = "73871d766de1e33a296eeb4f9faf2451f28bee39"


class Boltons3bfcfdd0(PythonProfile):
    owner = "mahmoud"
    repo = "boltons"
    commit = "3bfcfdd04395b6cc74a5c0cdc72c8f64cc4ac01f"


class BottleA8dfef30(PythonProfile):
    owner = "bottlepy"
    repo = "bottle"
    commit = "a8dfef301dec35f13e7578306002c40796651629"


class BoxA23451d2(PythonProfile):
    owner = "cdgriffith"
    repo = "Box"
    commit = "a23451d2869a511280eebe194efca41efadd2706"


class Cantools0c6a7871(PythonProfile):
    owner = "cantools"
    repo = "cantools"
    commit = "0c6a78711409e4307de34582f795ddb426d58dd8"
    install_cmds = ["pip install -e .[dev,plot]"]


class ChannelsA144b4b8(PythonProfile):
    owner = "django"
    repo = "channels"
    commit = "a144b4b8881a93faa567a6bdf2d7f518f4c16cd2"
    install_cmds = ["pip install -e .[tests,daphne]"]


class Chardet9630f238(PythonProfile):
    owner = "chardet"
    repo = "chardet"
    commit = "9630f2382faa50b81be2f96fd3dfab5f6739a0ef"


class CharsetNormalizer1fdd6463(PythonProfile):
    owner = "jawah"
    repo = "charset_normalizer"
    commit = "1fdd64633572040ab60e62e8b24f29cb7e17660b"


class ClickFde47b4b4(PythonProfile):
    owner = "pallets"
    repo = "click"
    commit = "fde47b4b4f978f179b9dff34583cb2b99021f482"


class Cloudpickle6220b0ce(PythonProfile):
    owner = "cloudpipe"
    repo = "cloudpickle"
    commit = "6220b0ce83ffee5e47e06770a1ee38ca9e47c850"


class ColorlogDfa10f59(PythonProfile):
    owner = "borntyping"
    repo = "python-colorlog"
    commit = "dfa10f59186d3d716aec4165ee79e58f2265c0eb"


class CookiecutterB4451231(PythonProfile):
    owner = "cookiecutter"
    repo = "cookiecutter"
    commit = "b4451231809fb9e4fc2a1e95d433cb030e4b9e06"


class Daphne32ac73e1(PythonProfile):
    owner = "django"
    repo = "daphne"
    commit = "32ac73e1a0fb87af0e3280c89fe4cc3ff1231b37"


class Dataset5c2dc8d3(PythonProfile):
    owner = "pudo"
    repo = "dataset"
    commit = "5c2dc8d3af1e0af0290dcd7ae2cae92589f305a1"
    install_cmds = ["python setup.py install"]


class DeepdiffEd252022(PythonProfile):
    owner = "seperman"
    repo = "deepdiff"
    commit = "ed2520229d0369813f6e54cdf9c7e68e8073ef62"
    install_cmds = ["pip install -r requirements-dev.txt", "pip install -e ."]


class DjangoMoney835c1ab8(PythonProfile):
    owner = "django-money"
    repo = "django-money"
    commit = "835c1ab867d11137b964b94936692bea67a038ec"
    install_cmds = ["pip install -e .[test,exchange]"]


class Dominate9082227e(PythonProfile):
    owner = "Knio"
    repo = "dominate"
    commit = "9082227e93f5a370012bb934286caf7385d3e7ac"


class Dotenv2b8635b7(PythonProfile):
    owner = "theskumar"
    repo = "python-dotenv"
    commit = "2b8635b79f1aa15cade0950117d4e7d12c298766"


class DrfNestedRouters6144169d(PythonProfile):
    owner = "alanjds"
    repo = "drf-nested-routers"
    commit = "6144169d5c33a1c5134b2fedac1d6cfa312c174e"
    install_cmds = ["pip install -r requirements.txt", "pip install -e ."]


class Environs73c372df(PythonProfile):
    owner = "sloria"
    repo = "environs"
    commit = "73c372df71002312615ad0349ae11274bb3edc69"
    install_cmds = ["pip install -e .[dev]"]


class Exceptiongroup0b4f4937(PythonProfile):
    owner = "agronholm"
    repo = "exceptiongroup"
    commit = "0b4f49378b585a338ae10abd72ec2006c5057d7b"


class Faker8b401a7d(PythonProfile):
    owner = "joke2k"
    repo = "faker"
    commit = "8b401a7d68f5fda1276f36a8fc502ef32050ed72"


class FeedparserCad965a3(PythonProfile):
    owner = "kurtmckee"
    repo = "feedparser"
    commit = "cad965a3f52c4b077221a2142fb14ef7f68cd576"


class Flake8Cf1542ce(PythonProfile):
    owner = "PyCQA"
    repo = "flake8"
    commit = "cf1542cefa3e766670b2066dd75c4571d682a649"


class FlashtextB316c7e9(PythonProfile):
    owner = "vi3k6i5"
    repo = "flashtext"
    commit = "b316c7e9e54b6b4d078462b302a83db85f884a94"


class FlaskBc098406(PythonProfile):
    owner = "pallets"
    repo = "flask"
    commit = "bc098406af9537aacc436cb2ea777fbc9ff4c5aa"


class Freezegun5f171db0(PythonProfile):
    owner = "spulec"
    repo = "freezegun"
    commit = "5f171db0aaa02c4ade003bbc8885e0bb19efbc81"


class Funcy207a7810(PythonProfile):
    owner = "Suor"
    repo = "funcy"
    commit = "207a7810c216c7408596d463d3f429686e83b871"


class FurlDa386f68(PythonProfile):
    owner = "gruns"
    repo = "furl"
    commit = "da386f68b8d077086c25adfd205a4c3d502c3012"


class FvcoreA491d5b9(PythonProfile):
    owner = "facebookresearch"
    repo = "fvcore"
    commit = "a491d5b9a06746f387aca2f1f9c7c7f28e20bef9"
    install_cmds = [
        "pip install torch shapely",
        "rm tests/test_focal_loss.py",
        "pip install -e .",
    ]


class GlomFb3c4e76(PythonProfile):
    owner = "mahmoud"
    repo = "glom"
    commit = "fb3c4e76f28816aebfd2538980e617742e98a7c2"


class Gpxpy09fc46b3(PythonProfile):
    owner = "tkrajina"
    repo = "gpxpy"
    commit = "09fc46b3cad16b5bf49edf8e7ae873794a959620"
    test_cmd = "pytest test.py --verbose --color=no --tb=no --disable-warnings"


class Grafanalib5c3b17ed(PythonProfile):
    owner = "weaveworks"
    repo = "grafanalib"
    commit = "5c3b17edaa437f0bc09b5f1b9275dc8fb91689fb"


class Graphene82903263(PythonProfile):
    owner = "graphql-python"
    repo = "graphene"
    commit = "82903263080b3b7f22c2ad84319584d7a3b1a1f6"


class GspreadA8be3b96(PythonProfile):
    owner = "burnash"
    repo = "gspread"
    commit = "a8be3b96f9276779ab680d84a0982282fb184000"


class GTTSDbcda4f39(PythonProfile):
    owner = "pndurette"
    repo = "gTTS"
    commit = "dbcda4f396074427172d4a1f798a172686ace6e0"


class GunicornBacbf8aa(PythonProfile):
    owner = "benoitc"
    repo = "gunicorn"
    commit = "bacbf8aa5152b94e44aa5d2a94aeaf0318a85248"


class H11Bed0dd4ae(PythonProfile):
    owner = "python-hyper"
    repo = "h11"
    commit = "bed0dd4ae9774b962b19833941bb9ec4dc403da9"


class IcecreamF76fef56(PythonProfile):
    owner = "gruns"
    repo = "icecream"
    commit = "f76fef56b66b59fd9a89502c60a99fbe28ee36bd"


class InflectC079a96a(PythonProfile):
    owner = "jaraco"
    repo = "inflect"
    commit = "c079a96a573ece60b54bd5210bb0f414beb74dcd"


class Iniconfig16793ead(PythonProfile):
    owner = "pytest-dev"
    repo = "iniconfig"
    commit = "16793eaddac67de0b8d621ae4e42e05b927e8d67"


class Isodate17cb25eb(PythonProfile):
    owner = "gweis"
    repo = "isodate"
    commit = "17cb25eb7bc3556a68f3f7b241313e9bb8b23760"


class JaxEbd90e06f(PythonProfile):
    owner = "jax-ml"
    repo = "jax"
    commit = "ebd90e06fa7caad087e2342431e3899cfd2fdf98"
    install_cmds = ['pip install -e ".[cpu]"']
    test_cmd = "pytest --disable-warnings --color=no --tb=no --verbose -n auto"
    min_testing = True
    min_pregold = True


class JinjaAda0a9a6(PythonProfile):
    owner = "pallets"
    repo = "jinja"
    commit = "ada0a9a6fc265128b46949b5144d2eaa55e6df2c"


class Jsonschema93e0caa5(PythonProfile):
    owner = "python-jsonschema"
    repo = "jsonschema"
    commit = "93e0caa5752947ec77333da81a634afe41a022ed"


class LangdetectA1598f1a(PythonProfile):
    owner = "Mimino666"
    repo = "langdetect"
    commit = "a1598f1afcbfe9a758cfd06bd688fbc5780177b2"


class LineProfilerA646bf0f(PythonProfile):
    owner = "pyutils"
    repo = "line_profiler"
    commit = "a646bf0f9ab3d15264a1be14d0d4ee6894966f6a"


class Markdownify6258f5c3(PythonProfile):
    owner = "matthewwithanm"
    repo = "python-markdownify"
    commit = "6258f5c38b97ab443b4ddf03e6676ce29b392d06"


class Markupsafe620c06c9(PythonProfile):
    owner = "pallets"
    repo = "markupsafe"
    commit = "620c06c919c1bd7bb1ce3dbee402e1c0c56e7ac3"


class Marshmallow9716fc62(PythonProfile):
    owner = "marshmallow-code"
    repo = "marshmallow"
    commit = "9716fc629976c9d3ce30cd15d270d9ac235eb725"


class MidoA0158ff9(PythonProfile):
    owner = "mido"
    repo = "mido"
    commit = "a0158ff95a08f9a4eef628a2e7c793fd3a466640"
    test_cmd = "pytest --disable-warnings --color=no --tb=no --verbose -rs -c /dev/null"


class MistuneBf54ef67(PythonProfile):
    owner = "lepture"
    repo = "mistune"
    commit = "bf54ef67390e02a5cdee7495d4386d7770c1902b"


class Nikola0f4c230e(PythonProfile):
    owner = "getnikola"
    repo = "nikola"
    commit = "0f4c230e5159e4e937463eb8d6d2ddfcbb09def2"
    install_cmds = ["pip install -e '.[extras,tests]'"]


class Oauthlib1fd52536(PythonProfile):
    owner = "oauthlib"
    repo = "oauthlib"
    commit = "1fd5253630c03e3f12719dd8c13d43111f66a8d2"


class Paramiko23f92003(PythonProfile):
    owner = "paramiko"
    repo = "paramiko"
    commit = "23f92003898b060df0e2b8b1d889455264e63a3e"
    test_cmd = "pytest -rA --color=no --disable-warnings"

    def log_parser(self, log: str) -> dict[str, str]:
        test_status_map = {}
        for line in log.split("\n"):
            for status in TestStatus:
                is_match = re.match(rf"^{status.value}\s(\S+)", line)
                if is_match:
                    test_status_map[is_match.group(1)] = status.value
                    continue
        return test_status_map


class Parse30da9e4f(PythonProfile):
    owner = "r1chardj0n3s"
    repo = "parse"
    commit = "30da9e4f37fdd979487c9fe2673df35b6b204c72"


class Parsimonious0d3f5f93(PythonProfile):
    owner = "erikrose"
    repo = "parsimonious"
    commit = "0d3f5f93c98ae55707f0958366900275d1ce094f"


class Parso338a5760(PythonProfile):
    owner = "davidhalter"
    repo = "parso"
    commit = "338a57602740ad0645b2881e8c105ffdc959e90d"
    install_cmds = ["python setup.py install"]


class PatsyA5d16484(PythonProfile):
    owner = "pydata"
    repo = "patsy"
    commit = "a5d1648401b0ea0649b077f4b98da27db947d2d0"
    install_cmds = ["pip install -e .[test]"]


class PdfminerSix1a8bd2f7(PythonProfile):
    owner = "pdfminer"
    repo = "pdfminer.six"
    commit = "1a8bd2f730295b31d6165e4d95fcb5a03793c978"


class Pdfplumber02ff4313(PythonProfile):
    owner = "jsvine"
    repo = "pdfplumber"
    commit = "02ff4313f846380fefccec9c73fb4c8d8a80d0ee"
    install_cmds = [
        "apt-get update && apt-get install ghostscript -y",
        "pip install -e .",
    ]


class PipdeptreeC31b6418(PythonProfile):
    owner = "tox-dev"
    repo = "pipdeptree"
    commit = "c31b641817f8235df97adf178ffd8e4426585f7a"
    install_cmds = [
        "apt-get update && apt-get install graphviz -y",
        "pip install -e .[test,graphviz]",
    ]


class PrettytableCa90b055(PythonProfile):
    owner = "prettytable"
    repo = "prettytable"
    commit = "ca90b055f20a6e8a06dcc46c2e3afe8ff1e8d0f1"


class Ptyprocess1067dbda(PythonProfile):
    owner = "pexpect"
    repo = "ptyprocess"
    commit = "1067dbdaf5cc3ab4786ae355aba7b9512a798734"


class Pyasn10f07d724(PythonProfile):
    owner = "pyasn1"
    repo = "pyasn1"
    commit = "0f07d7242a78ab4d129b26256d7474f7168cf536"


class Pydicom7d361b3d(PythonProfile):
    owner = "pydicom"
    repo = "pydicom"
    commit = "7d361b3d764dbbb1f8ad7af015e80ce96f6bf286"
    python_version = "3.11"


class PyfigletF8c5f35b(PythonProfile):
    owner = "pwaller"
    repo = "pyfiglet"
    commit = "f8c5f35be70a4bbf93ac032334311b326bc61688"


class Pygments27649ebbf(PythonProfile):
    owner = "pygments"
    repo = "pygments"
    commit = "27649ebbf5a2519725036b48ec99ef7745f100af"


class Pyopenssl04766a49(PythonProfile):
    owner = "pyca"
    repo = "pyopenssl"
    commit = "04766a496eb11f69f6226a5a0dfca4db90a5cbd1"


class Pyparsing533adf47(PythonProfile):
    owner = "pyparsing"
    repo = "pyparsing"
    commit = "533adf471f85b570006871e60a2e585fcda5b085"


class Pypika1c9646f0(PythonProfile):
    owner = "kayak"
    repo = "pypika"
    commit = "1c9646f0a019a167c32b649b6f5e6423c5ba2c9b"


class Pyquery811cd048(PythonProfile):
    owner = "gawel"
    repo = "pyquery"
    commit = "811cd048ffbe4e69fdc512863671131f98d691fb"


class PySnooper57472b46(PythonProfile):
    owner = "cool-RR"
    repo = "PySnooper"
    commit = "57472b4677b6c041647950f28f2d5750c38326c6"


class PythonDocx0cf6d71f(PythonProfile):
    owner = "python-openxml"
    repo = "python-docx"
    commit = "0cf6d71fb47ede07ecd5de2a8655f9f46c5f083d"


class PythonJsonLogger5f85723f(PythonProfile):
    owner = "madzak"
    repo = "python-json-logger"
    commit = "5f85723f4693c7289724fdcda84cfc0b62da74d4"


class PythonPinyinE42dede5(PythonProfile):
    owner = "mozillazg"
    repo = "python-pinyin"
    commit = "e42dede51abbc40e225da9a8ec8e5bd0043eed21"


class PythonPptx278b47b1(PythonProfile):
    owner = "scanny"
    repo = "python-pptx"
    commit = "278b47b1dedd5b46ee84c286e77cdfb0bf4594be"


class PythonQrcode456b01d4(PythonProfile):
    owner = "lincolnloop"
    repo = "python-qrcode"
    commit = "456b01d41f16e0cfb0f70c687848e276b78c3e8a"


class PythonReadability40256f40(PythonProfile):
    owner = "buriy"
    repo = "python-readability"
    commit = "40256f40389c1f97be5e83d7838547581653c6aa"


class PythonSlugify872b3750(PythonProfile):
    owner = "un33k"
    repo = "python-slugify"
    commit = "872b37509399a7f02e53f46ad9881f63f66d334b"
    test_cmd = "python test.py --verbose"


class Radon54b88e58(PythonProfile):
    owner = "rubik"
    repo = "radon"
    commit = "54b88e5878b2724bf4d77f97349588b811abdff2"


class Records5941ab27(PythonProfile):
    owner = "kennethreitz"
    repo = "records"
    commit = "5941ab2798cb91455b6424a9564c9cd680475fbe"


class RedDiscordBot33e0eac7(PythonProfile):
    owner = "Cog-Creators"
    repo = "Red-DiscordBot"
    commit = "33e0eac741955ce5b7e89d9b8f2f2712727af770"


class Result0b855e1e(PythonProfile):
    owner = "rustedpy"
    repo = "result"
    commit = "0b855e1e38a08d6f0a4b0138b10c127c01e54ab4"


class Safety7654596b(PythonProfile):
    owner = "pyupio"
    repo = "safety"
    commit = "7654596be933f8310b294dbc85a7af6066d06e4f"


class Scrapy35212ec5(PythonProfile):
    owner = "scrapy"
    repo = "scrapy"
    commit = "35212ec5b05a3af14c9f87a6193ab24e33d62f9f"
    install_cmds = [
        "apt-get update && apt-get install -y libxml2-dev libxslt-dev libjpeg-dev",
        "python -m pip install -e .",
        "rm tests/test_feedexport.py",
        "rm tests/test_pipeline_files.py",
    ]
    min_testing = True


class Schedule82a43db1(PythonProfile):
    owner = "dbader"
    repo = "schedule"
    commit = "82a43db1b938d8fdf60103bd41f329e06c8d3651"


class Schema24a30457(PythonProfile):
    owner = "keleshev"
    repo = "schema"
    commit = "24a3045773eac497c659f24b32f24a281be9f286"


class SoupsieveA8080d97(PythonProfile):
    owner = "facelessuser"
    repo = "soupsieve"
    commit = "a8080d97a0355e316981cb0c5c887a861c4244e3"


class Sqlfluff50a1c4b6(PythonProfile):
    owner = "sqlfluff"
    repo = "sqlfluff"
    commit = "50a1c4b6ff171188b6b70b39afe82a707b4919ac"
    min_testing = True


class Sqlglot036601ba(PythonProfile):
    owner = "tobymao"
    repo = "sqlglot"
    commit = "036601ba9cbe4d175d6a9d38bc27587eab858968"
    install_cmds = ['pip install -e ".[dev]"']
    min_testing = True


class SqlparseE57923b3(PythonProfile):
    owner = "andialbrecht"
    repo = "sqlparse"
    commit = "e57923b3aa823c524c807953cecc48cf6eec2cb2"


class Stackprinter219fcc52(PythonProfile):
    owner = "cknd"
    repo = "stackprinter"
    commit = "219fcc522fa5fd6e440703358f6eb408f3ffc007"


class StarletteDb5063c2(PythonProfile):
    owner = "encode"
    repo = "starlette"
    commit = "db5063c26030e019f7ee62aef9a1b564eca9f1d6"


class StringSimilarity115acaac(PythonProfile):
    owner = "luozhouyang"
    repo = "python-string-similarity"
    commit = "115acaacf926b41a15664bd34e763d074682bda3"


class SunpyF8edfd5c(PythonProfile):
    owner = "sunpy"
    repo = "sunpy"
    commit = "f8edfd5c4be873fbd28dec4583e7f737a045f546"
    python_version = "3.11"
    install_cmds = ['pip install -e ".[dev]"']
    min_testing = True


class Sympy2ab64612(PythonProfile):
    owner = "sympy"
    repo = "sympy"
    commit = "2ab64612efb287f09822419f4127878a4b664f71"
    install_cmds = ["pip install -e ."]
    min_testing = True
    min_pregold = True


class Tenacity0d40e76f(PythonProfile):
    owner = "jd"
    repo = "tenacity"
    commit = "0d40e76f7d06d631fb127e1ec58c8bd776e70d49"


class Termcolor3a42086f(PythonProfile):
    owner = "termcolor"
    repo = "termcolor"
    commit = "3a42086feb35647bc5aa5f1065b0327200da6b9b"


class TextdistanceC3aca916(PythonProfile):
    owner = "life4"
    repo = "textdistance"
    commit = "c3aca916bd756a8cb71114688b469ec90ef5b232"
    install_cmds = ['pip install -e ".[benchmark,test]"']


class TextfsmC31b6007(PythonProfile):
    owner = "google"
    repo = "textfsm"
    commit = "c31b600743895f018e7583f93405a3738a9f4d55"


class Thefuzz8a05a3ee(PythonProfile):
    owner = "seatgeek"
    repo = "thefuzz"
    commit = "8a05a3ee38cbd00a2d2f4bb31db34693b37a1fdd"


class Tinydb10644a0e(PythonProfile):
    owner = "msiemens"
    repo = "tinydb"
    commit = "10644a0e07ad180c5b756aba272ee6b0dbd12df8"


class Tldextract3d1bf184(PythonProfile):
    owner = "john-kurkowski"
    repo = "tldextract"
    commit = "3d1bf184d4f20fbdbadd6274560ccd438939160e"
    install_cmds = ["pip install -e .[testing]"]


class Tomli443a0c1b(PythonProfile):
    owner = "hukkin"
    repo = "tomli"
    commit = "443a0c1bc5da39b7ed84306912ee1900e6b72e2f"


class TornadoD5ac65c1(PythonProfile):
    owner = "tornadoweb"
    repo = "tornado"
    commit = "d5ac65c1f1453c2aeddd089d8e68c159645c13e1"
    test_cmd = "python -m tornado.test --verbose"

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


class TrioCfbbe2c1(PythonProfile):
    owner = "python-trio"
    repo = "trio"
    commit = "cfbbe2c1f96e93b19bc2577d2cab3f4fe2e81153"


class Tweepy91a41c6e(PythonProfile):
    owner = "tweepy"
    repo = "tweepy"
    commit = "91a41c6e1c955d278c370d51d5cf43b05f7cd979"
    install_cmds = ["pip install -e '.[dev,test,async]'"]


class TypeguardB6a7e438(PythonProfile):
    owner = "agronholm"
    repo = "typeguard"
    commit = "b6a7e4387c30a9f7d635712157c889eb073c1ea3"
    install_cmds = ["pip install -e .[test,doc]"]


class UsaddressA42a8f0c(PythonProfile):
    owner = "datamade"
    repo = "usaddress"
    commit = "a42a8f0c14bd2e273939fd51c604f10826301e73"
    install_cmds = ["pip install -e .[dev]"]


class VoluptuousA7a55f83(PythonProfile):
    owner = "alecthomas"
    repo = "voluptuous"
    commit = "a7a55f83b9fa7ba68b0669b3d78a61de703e0a16"


class WebargsDbde72fe(PythonProfile):
    owner = "marshmallow-code"
    repo = "webargs"
    commit = "dbde72fe5db8a999acd1716d5ef855ab7cc1a274"


class WordCloudEc24191c(PythonProfile):
    owner = "amueller"
    repo = "word_cloud"
    commit = "ec24191c64570d287032c5a4179c38237cd94043"


class Xmltodict0952f382(PythonProfile):
    owner = "martinblech"
    repo = "xmltodict"
    commit = "0952f382c2340bc8b86a5503ba765a35a49cf7c4"


class Yamllint8513d9b9(PythonProfile):
    owner = "adrienverge"
    repo = "yamllint"
    commit = "8513d9b97da3b32453b3fccb221f4ab134a028d7"


class Moto694ce1f4(PythonProfile):
    owner = "getmoto"
    repo = "moto"
    commit = "694ce1f4880c784fed0553bc19b2ace6691bc109"
    python_version = "3.12"
    install_cmds = ["make init"]
    min_testing = True


class MypyE93f06ce(PythonProfile):
    owner = "python"
    repo = "mypy"
    commit = "e93f06ceab81d8ff1f777c7587d04c339cfd5a16"
    python_version = "3.12"
    install_cmds = [
        "git submodule update --init mypy/typeshed || true",
        "python -m pip install -r test-requirements.txt",
        "python -m pip install -e .",
        "hash -r",
    ]
    test_cmd = "pytest --color=no -rA -k"
    min_testing = True

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


class MONAIa09c1f08(PythonProfile):
    owner = "Project-MONAI"
    repo = "MONAI"
    commit = "a09c1f08461cec3d2131fde3939ef38c3c4ad5fc"
    python_version = "3.12"
    install_cmds = [
        r"sed -i '/^git+https:\/\/github.com\/Project-MONAI\//d' requirements-dev.txt",
        "python -m pip install -U -r requirements-dev.txt",
        "python -m pip install -e .",
    ]
    test_cmd = "pytest --disable-warnings --color=no --tb=no --verbose"
    min_pregold = True
    min_testing = True


class Dvc1d6ea681(PythonProfile):
    owner = "iterative"
    repo = "dvc"
    commit = "1d6ea68133289ceab2637ce7095772678af792c6"
    install_cmds = ['pip install -e ".[dev]"']
    min_testing = True


class Hydra0f03eb60(PythonProfile):
    owner = "facebookresearch"
    repo = "hydra"
    commit = "0f03eb60c2ecd1fbdb25ede9a2c4faeac81de491"
    install_cmds = [
        "apt-get update && apt-get install -y openjdk-17-jdk openjdk-17-jre",
        "pip install -e .",
    ]
    min_testing = True


class Dask5f61e423(PythonProfile):
    owner = "dask"
    repo = "dask"
    commit = "5f61e42324c3a6cd4da17b5d5ebe4663aa4b8783"
    install_cmds = ["python -m pip install graphviz", "python -m pip install -e ."]
    min_testing = True


class Modin8c7799fd(PythonProfile):
    owner = "modin-project"
    repo = "modin"
    commit = "8c7799fdbbc2fb0543224160dd928215852b7757"
    install_cmds = ['pip install -e ".[all]"']
    min_pregold = True
    min_testing = True


class PydanticAcb0f10f(PythonProfile):
    owner = "pydantic"
    repo = "pydantic"
    commit = "acb0f10fda1c78441e052c57b4288bc91431f852"
    install_cmds = [
        "apt-get update && apt-get install -y locales pipx",
        "pipx install uv",
        "pipx install pre-commit",
        'export PATH="$HOME/.local/bin:$PATH"',
        "make install",
    ]
    test_cmd = (
        "/root/.local/bin/uv run pytest --disable-warnings --color=no --tb=no --verbose"
    )


class Conan86f29e13(PythonProfile):
    owner = "conan-io"
    repo = "conan"
    commit = "86f29e137a10bb6ed140c1a8c05c3099987b13c5"
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
    min_testing = True


class Pandas95280573(PythonProfile):
    owner = "pandas-dev"
    repo = "pandas"
    commit = "95280573e15be59036f98d82a8792599c10c6603"
    install_cmds = [
        "git remote add upstream https://github.com/pandas-dev/pandas.git",
        "git fetch upstream --tags",
        "python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true",
        """sed -i 's/__version__="[^"]*"/__version__="3.0.0.dev0+1992.g95280573e1"/' build/cp310/_version_meson.py""",
    ]
    min_pregold = True
    min_testing = True


class MonkeyType70c3acf6(PythonProfile):
    owner = "Instagram"
    repo = "MonkeyType"
    commit = "70c3acf62950be5dfb28743c7a719bfdecebcd84"


# Register all Python profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, PythonProfile)
        and obj != PythonProfile
    ):
        global_registry.register_profile(obj)
