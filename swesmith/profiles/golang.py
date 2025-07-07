import re

from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile, global_registry


@dataclass
class GoProfile(RepoProfile):
    """
    Profile for Golang repositories.

    This class provides Golang-specific defaults and functionality for
    repository profiles.
    """

    exts: list[str] = field(default_factory=lambda: [".go"])
    test_cmd: str = "go test -v ./..."

    @property
    def dockerfile(self):
        return f"""FROM golang:1.24
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN go mod tidy
RUN go test -v -count=1 ./... || true
"""

    def log_parser(self, log: str) -> dict[str, str]:
        """Parser for test logs generated with 'go test'"""
        test_status_map = {}

        pattern_status_map = [
            (re.compile(r"--- PASS: (\S+)"), TestStatus.PASSED.value),
            (re.compile(r"--- FAIL: (\S+)"), TestStatus.FAILED.value),
            (re.compile(r"FAIL:?\s?(.+?)\s"), TestStatus.FAILED.value),
            (re.compile(r"--- SKIP: (\S+)"), TestStatus.SKIPPED.value),
        ]
        for line in log.split("\n"):
            for pattern, status in pattern_status_map:
                match = pattern.match(line.strip())
                if match:
                    test_name = match.group(1)
                    test_status_map[test_name] = status
                    break

        return test_status_map


@dataclass
class Gin3c12d2a8(GoProfile):
    owner: str = "gin-gonic"
    repo: str = "gin"
    commit: str = "3c12d2a80e40930632fc4a4a4e1a45140f33fb12"


@dataclass
class Fzf976001e4(GoProfile):
    owner: str = "junegunn"
    repo: str = "fzf"
    commit: str = "976001e47459973b5e72565f3047cc9d9e20241d"


@dataclass
class Caddy77dd12cc(GoProfile):
    owner: str = "caddyserver"
    repo: str = "caddy"
    commit: str = "77dd12cc785990c5c5da947b4e883029ab8bd552"


@dataclass
class Cli4c47bad6(GoProfile):
    owner: str = "cli"
    repo: str = "cli"
    commit: str = "4c47bad604d8b206a4bc686507b2e9a3bed2b317"


@dataclass
class Concourse24abde66(GoProfile):
    owner: str = "concourse"
    repo: str = "concourse"
    commit: str = "24abde66ec91853eebdcf273a064e31accae9f25"


@dataclass
class Etcd721ba5bc(GoProfile):
    owner: str = "etcd-io"
    repo: str = "etcd"
    commit: str = "721ba5bc2489e0588b224a099a0fa369f166b4e5"


@dataclass
class Frp61330d4d(GoProfile):
    owner: str = "fatedier"
    repo: str = "frp"
    commit: str = "61330d4d794180c38d1f8ff7e9024b7f0f69d717"


@dataclass
class Gorm1e8baf54(GoProfile):
    owner: str = "go-gorm"
    repo: str = "gorm"
    commit: str = "1e8baf545953dd58e2f301f4dfef5febbc12da0f"


@dataclass
class Hugocfc8d315(GoProfile):
    owner: str = "gohugoio"
    repo: str = "hugo"
    commit: str = "cfc8d315b4f1a21c3daed0f9e78b7edb19f298d1"


@dataclass
class Grpcaa57e6af(GoProfile):
    owner: str = "grpc"
    repo: str = "grpc-go"
    commit: str = "aa57e6af6cbc8e1285315b338b092420f014c732"


@dataclass
class Istio8c687844(GoProfile):
    owner: str = "istio"
    repo: str = "istio"
    commit: str = "8c687844a88bfc4a7d4f998e4c950cd9243334c3"


@dataclass
class Lazygit91d8c251(GoProfile):
    owner: str = "jesseduffield"
    repo: str = "lazygit"
    commit: str = "91d8c25183fde8e0d9ae51b8a24acb545b9cb278"


@dataclass
class Echo98ca08e7(GoProfile):
    owner: str = "labstack"
    repo: str = "echo"
    commit: str = "98ca08e7dd64075b858e758d6693bf9799340756"


@dataclass
class Natsserver2ee2e24c(GoProfile):
    owner: str = "nats-io"
    repo: str = "nats-server"
    commit: str = "2ee2e24cb10924adb699ecb68b89e8ce2523ea75"


@dataclass
class Addressec203a4f(GoProfile):
    owner: str = "bojanz"
    repo: str = "address"
    commit: str = "ec203a4f7f569c03a0f83e2e749b63947481fe4c"


@dataclass
class Prometheus74aca682(GoProfile):
    owner: str = "prometheus"
    repo: str = "prometheus"
    commit: str = "74aca682b77d66f5761bd68459f3b570ec34ce2d"


@dataclass
class Syncthing06dd8ee(GoProfile):
    owner: str = "syncthing"
    repo: str = "syncthing"
    commit: str = "06dd8ee6d75e14a62b7da28b2eec33f2f5695fc8"


@dataclass
class Gozero75cebb65(GoProfile):
    owner: str = "zeromicro"
    repo: str = "go-zero"
    commit: str = "75cebb65f88cc6019d9e16e34c4a567e621f4dd5"


@dataclass
class Goatcounter854b1dd2(GoProfile):
    owner: str = "arp242"
    repo: str = "goatcounter"
    commit: str = "854b1dd2408ca95645ad03ea3fd01ccfe267261a"


@dataclass
class Gotests16a93f6e(GoProfile):
    owner: str = "cweill"
    repo: str = "gotests"
    commit: str = "16a93f6eb6519118b1d282e2f233596a98dd7e96"


@dataclass
class Aferof5375068(GoProfile):
    owner: str = "spf13"
    repo: str = "afero"
    commit: str = "f5375068505ede77db8f13bfb1069011fab77063"


@dataclass
class Color5a495618(GoProfile):
    owner: str = "gookit"
    repo: str = "color"
    commit: str = "5a4956180d841b68a25a68cb632aea0128845a5a"


@dataclass
class Goprompt82a91227(GoProfile):
    owner: str = "c-bata"
    repo: str = "go-prompt"
    commit: str = "82a912274504477990ecf7c852eebb7c85291772"


@dataclass
class Progressbar(GoProfile):
    owner: str = "schollz"
    repo: str = "progressbar"
    commit: str = "1a5d48397714b88f8a54612e40514f2fb5e44127"


@dataclass
class Accounting(GoProfile):
    owner: str = "leekchan"
    repo: str = "accounting"
    commit: str = "2e09117338f81558182056c197506abceadc83e0"


@dataclass
class Mpb(GoProfile):
    owner: str = "vbauerster"
    repo: str = "mpb"
    commit: str = "d30b560650ec806c82029422335904404814e220"


@dataclass
class Bubbletea(GoProfile):
    owner: str = "charmbracelet"
    repo: str = "bubbletea"
    commit: str = "ca9473b2d93dc3abce4f8b634e11a4b351517a84"


@dataclass
class Fx(GoProfile):
    owner: str = "antonmedv"
    repo: str = "fx"
    commit: str = "1ab8a99b7cfd5bb4242677a5215e000c69b8b9e0"


@dataclass
class Spinner(GoProfile):
    owner: str = "briandowns"
    repo: str = "spinner"
    commit: str = "55430861f77b20de3f456775b00c706519464f36"


@dataclass
class UIProgress(GoProfile):
    owner: str = "gosuri"
    repo: str = "uiprogress"
    commit: str = "484b9f69ea000422e1873db136dbb80e30b5de3c"


@dataclass
class Cobra(GoProfile):
    owner: str = "spf13"
    repo: str = "cobra"
    commit: str = "6dec1ae26659a130bdb4c985768d1853b0e1bc06"


@dataclass
class Dnote(GoProfile):
    owner: str = "dnote"
    repo: str = "dnote"
    commit: str = "895dcaa59f1c649f0a5d5703e08ae6a96304d03d"


@dataclass
class GoFlags(GoProfile):
    owner: str = "jessevdk"
    repo: str = "go-flags"
    commit: str = "8eae68f0a7870eec41bc8061c2194040048cdf59"


@dataclass
class PFlag(GoProfile):
    owner: str = "spf13"
    repo: str = "pflag"
    commit: str = "1c62fb2813da5f1d1b893a49180a41b3f6be3262"


@dataclass
class Liner(GoProfile):
    owner: str = "peterh"
    repo: str = "liner"
    commit: str = "58a158787cd552b11ce4a45f589a5452072c1fc0"


@dataclass
class Env(GoProfile):
    owner: str = "caarlos0"
    repo: str = "env"
    commit: str = "56a09d295d9321b1f3b537fd23df1527011cd83d"


@dataclass
class Godotenv(GoProfile):
    owner: str = "joho"
    repo: str = "godotenv"
    commit: str = "3a7a19020151b45a29896c9142723efe5b11a061"


@dataclass
class Hjsongo(GoProfile):
    owner: str = "hjson"
    repo: str = "hjson-go"
    commit: str = "f3219653412abdb7bf061c55f58bde481db46051"


@dataclass
class Sonic(GoProfile):
    owner: str = "bytedance"
    repo: str = "sonic"
    commit: str = "de4f017fca6448580003b6cc661bed8fded68d1d"


@dataclass
class Muffet(GoProfile):
    owner: str = "raviqqe"
    repo: str = "muffet"
    commit: str = "430e693772b88a413ff23214e026daff3f05f82a"


@dataclass
class Omniparser(GoProfile):
    owner: str = "jf-tech"
    repo: str = "omniparser"
    commit: str = "d4371ab77afacd626b21d925e0e5b7989298e847"


@dataclass
class Roaring(GoProfile):
    owner: str = "RoaringBitmap"
    repo: str = "roaring"
    commit: str = "09c46a0a47d21ebbe4bedb01bbcf0ba96f22a46d"


@dataclass
class Bitset(GoProfile):
    owner: str = "bits-and-blooms"
    repo: str = "bitset"
    commit: str = "167865a24c4956c76a987f0a7612f9ac04b93a82"


@dataclass
class BoomFilters(GoProfile):
    owner: str = "tylertreat"
    repo: str = "BoomFilters"
    commit: str = "db6545748bc4726eb9410c6763c7e4035d6ccba3"

    @property
    def dockerfile(self):
        return f"""FROM golang:1.24
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN go mod init github.com/tylertreat/BoomFilters
RUN go mod tidy
"""


@dataclass
class Ini(GoProfile):
    owner: str = "go-ini"
    repo: str = "ini"
    commit: str = "b2f570e5b5b844226bbefe6fb521d891f529a951"

    @property
    def dockerfile(self):
        return f"""FROM golang:1.24
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN go mod init github.com/go-ini/ini
RUN go mod tidy
"""


@dataclass
class GoDatastructures(GoProfile):
    owner: str = "Workiva"
    repo: str = "go-datastructures"
    commit: str = "18d77378f834b72b39509b12f70f3f9915c56884"


@dataclass
class Gods(GoProfile):
    owner: str = "emirpasic"
    repo: str = "gods"
    commit: str = "1d83d5ae39fbb0de45a60365791ff1c8b9bae953"


@dataclass
class Gota(GoProfile):
    owner: str = "go-gota"
    repo: str = "gota"
    commit: str = "f70540952827cfc8abfa1257391fd33284300b24"


@dataclass
class GolangSet(GoProfile):
    owner: str = "deckarep"
    repo: str = "golang-set"
    commit: str = "9480c3eb4dae7f17ca7edac65e4b48690c199993"


@dataclass
class Bleve(GoProfile):
    owner: str = "blevesearch"
    repo: str = "bleve"
    commit: str = "f2876b5e34763ac2d28a75a87dce5f2ff4a64d42"
    timeout: int = 120
    timeout_ref: int = 120


@dataclass
class GoAdaptiveRadixTree(GoProfile):
    owner: str = "plar"
    repo: str = "go-adaptive-radix-tree"
    commit: str = "63c2eff3ccd16d8ae93d963e4b9b33d8f537f82a"


@dataclass
class Trie(GoProfile):
    owner: str = "derekparker"
    repo: str = "trie"
    commit: str = "4095f8e392f77af6b669912d51d17233582a1ba9"


@dataclass
class Bigcache(GoProfile):
    owner: str = "allegro"
    repo: str = "bigcache"
    commit: str = "5aa251c4cc3d607bbb48b825ef583ad1fafa1845"


@dataclass
class Cache2go(GoProfile):
    owner: str = "muesli"
    repo: str = "cache2go"
    commit: str = "518229cd8021d8568e4c6c13743bb050dc1f3a05"


@dataclass
class Fastcache(GoProfile):
    owner: str = "VictoriaMetrics"
    repo: str = "fastcache"
    commit: str = "b7ccf30b0eb69939f4031063a57ec4124f964b00"


@dataclass
class Gcache(GoProfile):
    owner: str = "bluele"
    repo: str = "gcache"
    commit: str = "d8b7e051c564c174fea6ef60d180abf601099015"


@dataclass
class Groupcache(GoProfile):
    owner: str = "golang"
    repo: str = "groupcache"
    commit: str = "2c02b8208cf8c02a3e358cb1d9b60950647543fc"


@dataclass
class Otter(GoProfile):
    owner: str = "maypok86"
    repo: str = "otter"
    commit: str = "20ae57f9b2e4400638be8da5183163d410f0186b"


@dataclass
class Ristretto(GoProfile):
    owner: str = "hypermodeinc"
    repo: str = "ristretto"
    commit: str = "da5701167d70aac45473f5ea98099b118505eef5"


@dataclass
class Sturdyc(GoProfile):
    owner: str = "viccon"
    repo: str = "sturdyc"
    commit: str = "97fc006bbf4a7f1f09922fa77a9444e5ce3a20ad"


@dataclass
class Ttlcache(GoProfile):
    owner: str = "jellydator"
    repo: str = "ttlcache"
    commit: str = "7145e12e34f243c69a0f7b5f6b86a832ad8b4fc8"


@dataclass
class Ledisdb(GoProfile):
    owner: str = "ledisdb"
    repo: str = "ledisdb"
    commit: str = "d35789ec47e667726160e227e7c05e09627a6d6c"


@dataclass
class Buntdb(GoProfile):
    owner: str = "tidwall"
    repo: str = "buntdb"
    commit: str = "3daff4e1233584685027938bde39971cc239f2b2"


@dataclass
class Column(GoProfile):
    owner: str = "kelindar"
    repo: str = "column"
    commit: str = "b35d478cda58087266d177b265bc8b29859c721e"


@dataclass
class Diskv(GoProfile):
    owner: str = "peterbourgon"
    repo: str = "diskv"
    commit: str = "2566386005f64f58f34e1ff32907800a64537e6a"


@dataclass
class Eliasdb(GoProfile):
    owner: str = "krotik"
    repo: str = "eliasdb"
    commit: str = "88a1da66df9527aa97e8781dfc91cb9feb08125c"


@dataclass
class Godis(GoProfile):
    owner: str = "HDT3213"
    repo: str = "godis"
    commit: str = "8a81b9112aa50d5ae07584291ddb9f80122f0246"


@dataclass
class Moss(GoProfile):
    owner: str = "couchbase"
    repo: str = "moss"
    commit: str = "bf10bab20a24b43c15d23b530fc848e7bb580cad"


@dataclass
class Pogreb(GoProfile):
    owner: str = "akrylysov"
    repo: str = "pogreb"
    commit: str = "76e9512dfd3d100f0032dfa30e77a447b3cbe65c"


@dataclass
class Redka(GoProfile):
    owner: str = "nalgeon"
    repo: str = "redka"
    commit: str = "7c532df931237186942d480e00129ae9436da7ad"


@dataclass
class Rosedb(GoProfile):
    owner: str = "rosedblabs"
    repo: str = "rosedb"
    commit: str = "4af513fe955f755f7af391e6466b09f50ae8cd7f"


@dataclass
class Atlas(GoProfile):
    owner: str = "ariga"
    repo: str = "atlas"
    commit: str = "1afaaba2acfdae2a0c940e784a5465e9be00155d"


@dataclass
class Dbmate(GoProfile):
    owner: str = "amacneil"
    repo: str = "dbmate"
    commit: str = "241976bfba6de9008c65b4cf020a56d7372abfda"


@dataclass
class Avro(GoProfile):
    owner: str = "hamba"
    repo: str = "avro"
    commit: str = "ec06b38c0b47ba397a439479d9f43dc92d547b5"


@dataclass
class Goose(GoProfile):
    owner: str = "pressly"
    repo: str = "goose"
    commit: str = "f2b5a9d8bcd75d257ff9b484e79e2edb94dd0b8c"


@dataclass
class Skeema(GoProfile):
    owner: str = "skeema"
    repo: str = "skeema"
    commit: str = "defb0097f48c8dfd2d239c6fff4259000fcfee59"


@dataclass
class Sqlmigrate(GoProfile):
    owner: str = "rubenv"
    repo: str = "sql-migrate"
    commit: str = "563a2f031824f380dfadda9a5886679d883420f3"


@dataclass
class Chproxy(GoProfile):
    owner: str = "ContentSquare"
    repo: str = "chproxy"
    commit: str = "a9364c8b7923adfb1bf02d28e2298bf46eec5559"


@dataclass
class ClickhouseBulk(GoProfile):
    owner: str = "nikepan"
    repo: str = "clickhouse-bulk"
    commit: str = "cdc261cb029f4d493fa825a6edffe3f2f1b81f1e"


@dataclass
class Prest(GoProfile):
    owner: str = "prest"
    repo: str = "prest"
    commit: str = "c54ddd30b1ed3ebe24bb1dc3db696d107e5d40c4"


@dataclass
class Rdb(GoProfile):
    owner: str = "HDT3213"
    repo: str = "rdb"
    commit: str = "087190b9f7c7cee3c47192f6cdc9197bf6f30265"


@dataclass
class Dbq(GoProfile):
    owner: str = "rocketlaunchr"
    repo: str = "dbq"
    commit: str = "edab5e1151162737bd48e6dd04eec376c44063a2"


@dataclass
class Goqu(GoProfile):
    owner: str = "doug-martin"
    repo: str = "goqu"
    commit: str = "21b6e6d1cb1befe839044764d8ad6b1c6f0b5ef4"


@dataclass
class Sqlc(GoProfile):
    owner: str = "sqlc-dev"
    repo: str = "sqlc"
    commit: str = "b34aa37208de9158bc13581ce673389e32e86680"


@dataclass
class Squirrel(GoProfile):
    owner: str = "Masterminds"
    repo: str = "squirrel"
    commit: str = "1ded5784535dcffa4e175d4efbd1ca2706927758"


@dataclass
class Sqlingo(GoProfile):
    owner: str = "lqs"
    repo: str = "sqlingo"
    commit: str = "ed36ef030f789fb664e8d22d63bc03eceb45343d"

    @property
    def dockerfile(self):
        return f"""FROM golang:1.24
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN go mod init github.com/lqs/sqlingo
RUN go mod tidy
"""


@dataclass
class Dotsql(GoProfile):
    owner: str = "qustavo"
    repo: str = "dotsql"
    commit: str = "5d06b8903af8416d86b205c175b22ee903d869c8"


@dataclass
class GoMssqldb(GoProfile):
    owner: str = "denisenkom"
    repo: str = "go-mssqldb"
    commit: str = "103f0369fa02aac21aae282e4f7f81c903aba6be"


@dataclass
class Mysql(GoProfile):
    owner: str = "go-sql-driver"
    repo: str = "mysql"
    commit: str = "76c00e35a8d48f8f70f0e7dffe584692bd3fa612"


@dataclass
class GoSqlite3(GoProfile):
    owner: str = "mattn"
    repo: str = "go-sqlite3"
    commit: str = "f76bae4b0044cbba8fb2c72b8e4559e8fbcffd86"


@dataclass
class Godror(GoProfile):
    owner: str = "godror"
    repo: str = "godror"
    commit: str = "cc3b65ef71b255472470aad349098e6663cba6cf"


@dataclass
class Ksql(GoProfile):
    owner: str = "VinGarcia"
    repo: str = "ksql"
    commit: str = "dadb4199eea95cfc4499f9bf4001feccbea86afd"


@dataclass
class Sqlhooks(GoProfile):
    owner: str = "qustavo"
    repo: str = "sqlhooks"
    commit: str = "7875602513fa745b19df8c03f4d31c00b61be6d4"


@dataclass
class Richgo(GoProfile):
    owner: str = "kyoh86"
    repo: str = "richgo"
    commit: str = "98af5f3a762dabdd7f3c30a122a7950fc3cdb4f1"


@dataclass
class Gotests(GoProfile):
    owner: str = "cweill"
    repo: str = "gotests"
    commit: str = "16a93f6eb6519118b1d282e2f233596a98dd7e96"


@dataclass
class GoImportsReviser(GoProfile):
    owner: str = "incu6us"
    repo: str = "goimports-reviser"
    commit: str = "fb560c58db94476809ad5d99d4171dc0db4000d2"


@dataclass
class Wrapcheck(GoProfile):
    owner: str = "tomarrell"
    repo: str = "wrapcheck"
    commit: str = "486d5bbebfef0d94d5ff15b57e01821f6407bb52"


@dataclass
class Todocheck(GoProfile):
    owner: str = "presmihaylov"
    repo: str = "todocheck"
    commit: str = "f0fae9b573374fc0df2ff7f07a7f4693602ae846"


@dataclass
class Revive(GoProfile):
    owner: str = "mgechev"
    repo: str = "revive"
    commit: str = "03e81029a89342ec7107a3655241f479065e208d"


@dataclass
class PhpParser(GoProfile):
    owner: str = "z7zmey"
    repo: str = "php-parser"
    commit: str = "367eff9de651fb9479c98f4f3741db3195e549ad"


@dataclass
class GolangCILint(GoProfile):
    owner: str = "golangci"
    repo: str = "golangci-lint"
    commit: str = "4fe2e59ba9cbe6022d35edac72f671eff3f07354"
    timeout: int = 120
    timeout_ref: int = 120


@dataclass
class Errcheck(GoProfile):
    owner: str = "kisielk"
    repo: str = "errcheck"
    commit: str = "dacab891ef4a1c38ecf6c4d94fd66746bb1247d5"


@dataclass
class Dupl(GoProfile):
    owner: str = "mibk"
    repo: str = "dupl"
    commit: str = "1bf052b6e6431cb666549323351baf3b2aa741e4"


@dataclass
class GoCritic(GoProfile):
    owner: str = "go-critic"
    repo: str = "go-critic"
    commit: str = "db2ec6f4d1f42bbe7fe2cd47f311243bbd1b3398"


@dataclass
class GoCleanarch(GoProfile):
    owner: str = "roblaszczak"
    repo: str = "go-cleanarch"
    commit: str = "03b96056c4c9ff2a739629f1e39f32715d3f9e65"


@dataclass
class GoModOutdated(GoProfile):
    owner: str = "psampaz"
    repo: str = "go-mod-outdated"
    commit: str = "bb79367d102a05221196613dde574f1a0b81b556"


@dataclass
class Xpath(GoProfile):
    owner: str = "antchfx"
    repo: str = "xpath"
    commit: str = "8d50c252d867285812177ffd3ff0924104ffb1eb"


@dataclass
class Bone(GoProfile):
    owner: str = "go-zoo"
    repo: str = "bone"
    commit: str = "31c3a0bb520c6d7a63dbb942459a3067787a975e"


@dataclass
class Chi(GoProfile):
    owner: str = "go-chi"
    repo: str = "chi"
    commit: str = "23c395f8524a30334126ca16fb4d37b88745b9b9"


@dataclass
class Httprouter(GoProfile):
    owner: str = "julienschmidt"
    repo: str = "httprouter"
    commit: str = "484018016424d215c0b87c42f4c9b57d980fbd00"


@dataclass
class Httptreemux(GoProfile):
    owner: str = "dimfeld"
    repo: str = "httptreemux"
    commit: str = "53a6a09954e8593e66a0c372335c0e96b318b920"


# Register all Go profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, GoProfile)
        and obj.__name__ != "GoProfile"
    ):
        global_registry.register_profile(obj)
