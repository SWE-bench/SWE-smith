import re
from dataclasses import dataclass, field

from swesmith.constants import ENV_NAME
from swesmith.profiles.base import RepoProfile, registry

from swesmith.profiles.javascript import (
    parse_log_jasmine,
    parse_log_jest,
    parse_log_mocha,
    parse_log_vitest,
)


@dataclass
class TypeScriptProfile(RepoProfile):
    """
    Profile for TypeScript repositories.
    """

    exts: list[str] = field(default_factory=lambda: [".ts", ".tsx"])

    def extract_entities(
        self,
        dirs_exclude: list[str] | None = None,
        dirs_include: list[str] = [],
        exclude_tests: bool = True,
        max_entities: int = -1,
    ) -> list:
        """
        Override to exclude TypeScript/JavaScript build artifacts by default.
        """
        if dirs_exclude is None:
            dirs_exclude = [
                "dist",
                "build",
                "node_modules",
                "coverage",
                ".next",
                "out",
                "examples",
                "docs",
                "bin",
                "lib",
            ]

        return super().extract_entities(
            dirs_exclude=dirs_exclude,
            dirs_include=dirs_include,
            exclude_tests=exclude_tests,
            max_entities=max_entities,
        )


def default_npm_install_dockerfile(mirror_name: str, node_version: str = "20") -> str:
    """Default Dockerfile for TypeScript projects using npm."""
    return f"""FROM node:{node_version}-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN npm install
"""


def default_pnpm_install_dockerfile(mirror_name: str, node_version: str = "20") -> str:
    """Default Dockerfile for TypeScript projects using pnpm."""
    return f"""FROM node:{node_version}-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm
RUN git clone https://github.com/{mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN pnpm install
"""


@dataclass
class CrossEnv9951937a(TypeScriptProfile):
    owner: str = "kentcdodds"
    repo: str = "cross-env"
    commit: str = "9951937a7d3d4a1ea7bd2ce3133bcfb687125813"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim
RUN apt-get update && apt-get install -y git procps && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN npm install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Trpc2f40ba93(TypeScriptProfile):
    owner: str = "trpc"
    repo: str = "trpc"
    commit: str = "2f40ba935ad7f7d29eec3f9c45d353450b43e852"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:22
RUN apt-get update && apt-get install -y git procps && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN pnpm install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class ClassValidator977d2c70(TypeScriptProfile):
    owner: str = "typestack"
    repo: str = "class-validator"
    commit: str = "977d2c707930db602b6450d0c03ee85c70756f1f"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim
RUN apt-get update && apt-get install -y git procps && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN npm install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class NextChatc3b8c158(TypeScriptProfile):
    owner: str = "ChatGPTNextWeb"
    repo: str = "NextChat"
    commit: str = "c3b8c1587c04fff05f7b42276a43016e87771527"
    test_cmd: str = (
        "node --no-warnings --experimental-vm-modules $(yarn bin jest) --ci --forceExit"
    )

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN yarn install
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Cherrystudiob767d6e2(TypeScriptProfile):
    owner: str = "CherryHQ"
    repo: str = "cherry-studio"
    commit: str = "b767d6e2bff302740f2e6d8e49b8cec221147a4d"
    test_cmd: str = (
        "pnpm vitest run --reporter=verbose --silent --passWithNoTests || true"
    )

    @property
    def dockerfile(self):
        return f"""FROM node:22-alpine

RUN apk add --no-cache git python3 make g++ gcc musl-dev

# Clone ONLY the main repo to save space (avoiding --recurse-submodules)
RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed

# Install pnpm and dependencies, skipping scripts and cleaning cache
RUN npm install -g pnpm@10.27.0 &&     pnpm install --ignore-scripts &&     pnpm store prune

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class CopilotKitfd993504(TypeScriptProfile):
    owner: str = "CopilotKit"
    repo: str = "CopilotKit"
    commit: str = "fd993504783b31ed2374252d6667c47ff9b32980"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${{PATH}}"

RUN npm install -g pnpm@10.13.1

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class RSSHubee161b72(TypeScriptProfile):
    owner: str = "DIYgod"
    repo: str = "RSSHub"
    commit: str = "ee161b72e4da5200213850cb03defd50e4452ecf"
    test_cmd: str = "pnpm vitest run"

    @property
    def dockerfile(self):
        return f"""FROM node:22

RUN corepack enable && corepack prepare pnpm@10.28.2 --activate

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install

CMD ["pnpm", "start"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Dokploy1e7522d1(TypeScriptProfile):
    owner: str = "Dokploy"
    repo: str = "dokploy"
    commit: str = "1e7522d1731f8c50ea65970e5ac129f2417c2a38"
    test_cmd: str = "pnpm --filter dokploy run test --run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.12.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Effect5df4da10(TypeScriptProfile):
    owner: str = "Effect-TS"
    repo: str = "effect"
    commit: str = "5df4da10de444f379a166f4b28721e75100bb838"
    test_cmd: str = "pnpm vitest run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.17.1

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

# Remove the problematic @effect/docgen dependency that's causing 404
RUN sed -i '/"@effect\\/docgen":/d' package.json

RUN pnpm install --no-frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Fuelstsb3f37c91(TypeScriptProfile):
    owner: str = "FuelLabs"
    repo: str = "fuels-ts"
    commit: str = "b3f37c91aca4aa9d5e4c0d3967f66237190826ea"
    test_cmd: str = "pnpm test:node"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN npm install -g pnpm@9.4.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install && pnpm build:packages

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class FigmaContextMCPc7304173(TypeScriptProfile):
    owner: str = "GLips"
    repo: str = "Figma-Context-MCP"
    commit: str = "c73041730cb2b288a32c6c6ba4b48d8970841659"
    test_cmd: str = "pnpm test -- src/tests/benchmark.test.ts"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.10.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["pnpm", "start"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Gitbook81f8ddcf(TypeScriptProfile):
    owner: str = "GitbookIO"
    repo: str = "gitbook"
    commit: str = "81f8ddcf27ec398a33b6f676a81e9a791b673ce2"
    test_cmd: str = "bun run unit"

    @property
    def dockerfile(self):
        return f"""FROM oven/bun:1.3.7

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN bun install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Reactselect052e864b(TypeScriptProfile):
    owner: str = "JedWatson"
    repo: str = "react-select"
    commit: str = "052e864b4990a67c4ee416851c34d1eb7b58267b"
    test_cmd: str = "npx jest --coverage --no-cache"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Metamaskextension5b029fa6(TypeScriptProfile):
    owner: str = "MetaMask"
    repo: str = "metamask-extension"
    commit: str = "5b029fa6759efdaa18c597efc253ad38d2822488"
    test_cmd: str = "yarn test:unit --ci --reporters=default --reporters=jest-junit --outputFile=test-results.xml"

    @property
    def dockerfile(self):
        return f"""FROM node:24

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn set version 4.12.0

RUN yarn install --immutable

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class NativeScript3d6a4392(TypeScriptProfile):
    owner: str = "NativeScript"
    repo: str = "NativeScript"
    commit: str = "3d6a4392f6008e4f43f8f5439a256c50e3707101"
    test_cmd: str = "npx nx run-many --target=test --all --parallel=1 --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install --legacy-peer-deps

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class OpenCute84c0cfd(TypeScriptProfile):
    owner: str = "OpenCut-app"
    repo: str = "OpenCut"
    commit: str = "e84c0cfda6784abb9bcb72aae757233cd8951780"
    test_cmd: str = "bun test"

    @property
    def dockerfile(self):
        return f"""FROM oven/bun:1.2.18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN bun install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


# @dataclass
# class Qwencodea38a5ba8(TypeScriptProfile):
#     owner: str = "QwenLM"
#     repo: str = "qwen-code"
#     commit: str = "a38a5ba87d0642368b93acbf5ca8822277810e7e"
#     test_cmd: str = "npm test --workspaces --if-present --parallel"

#     @property
#     def dockerfile(self):
#         return f"""FROM node:20-slim

# RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

# RUN git clone https://github.com/{self.mirror_name}.git /testbed
# WORKDIR /testbed
# RUN git submodule update --init --recursive

# RUN npm install

# CMD ["/bin/bash"]"""

#     def log_parser(self, log: str) -> dict[str, str]:
#         return parse_log_jest(log)


@dataclass
class Folo62efdd29(TypeScriptProfile):
    owner: str = "RSSNext"
    repo: str = "Folo"
    commit: str = "62efdd29b21fce9681e4e1497b6ab7084e5a41b0"
    test_cmd: str = "pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.17.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Rxjsc15b37f8(TypeScriptProfile):
    owner: str = "ReactiveX"
    repo: str = "rxjs"
    commit: str = "c15b37f81ba5f5abea8c872b0189a70b150df4cb"
    test_cmd: str = "yarn nx run rxjs:test --reporter spec"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Redocd41fd46f(TypeScriptProfile):
    owner: str = "Redocly"
    repo: str = "redoc"
    commit: str = "d41fd46f7cbee86bf83dc17b7ec51baf54f72a54"
    test_cmd: str = "npm run unit"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Queryd6884583(TypeScriptProfile):
    owner: str = "TanStack"
    repo: str = "query"
    commit: str = "d68845833b19e9168e6f822b413d5124c8c5904c"
    test_cmd: str = "pnpm run test:ci"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.24.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Unleash120f50bc(TypeScriptProfile):
    owner: str = "Unleash"
    repo: str = "unleash"
    commit: str = "120f50bcd0e939699162d572c975974a57ea7cfc"
    test_cmd: str = (
        "NODE_ENV=test PORT=4243 npx vitest run --config vitest.unit.config.ts src/lib"
    )

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn install
RUN yarn run build:backend

RUN printf 'import {{ defineConfig }} from "vitest/config";\\nexport default defineConfig({{ test: {{ globals: true, environment: "node" }} }});\\n' > vitest.unit.config.ts

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Million13406265(TypeScriptProfile):
    owner: str = "aidenybai"
    repo: str = "million"
    commit: str = "1340626556600ae75c352aa6a30ac6c1f96fe97b"
    test_cmd: str = "pnpm vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN corepack enable && corepack prepare pnpm@9.1.4 --activate

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class SponsorBlockdfddffbc(TypeScriptProfile):
    owner: str = "ajayyy"
    repo: str = "SponsorBlock"
    commit: str = "dfddffbc5128dbc55b4dc7c83cdcd18787f48ba4"
    test_cmd: str = "npx jest"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN npm install
RUN cp config.json.example config.json && npm run build:chrome
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Bulletproofreact63f68340(TypeScriptProfile):
    owner: str = "alan2207"
    repo: str = "bulletproof-react"
    commit: str = "63f68340798e1f0e8f3d04732152a5146f827d04"
    test_cmd: str = "VITE_APP_API_URL=http://localhost:3000 yarn vitest run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

WORKDIR /testbed/apps/react-vite

RUN corepack enable && yarn install --frozen-lockfile

ENV VITE_APP_API_URL=http://localhost:3000

CMD ["yarn", "test"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Antdesignpro607e63f4(TypeScriptProfile):
    owner: str = "ant-design"
    repo: str = "ant-design-pro"
    commit: str = "607e63f4fdb49d78306a618f2b2c29291ce85500"
    test_cmd: str = "npm test -- --ci --colors --no-cache"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Antdesignef322504(TypeScriptProfile):
    owner: str = "ant-design"
    repo: str = "ant-design"
    commit: str = "ef32250465cdbb4521c084e4189499a7d45491e2"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install --legacy-peer-deps

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class G2e58f72b1(TypeScriptProfile):
    owner: str = "antvis"
    repo: str = "G2"
    commit: str = "e58f72b19aa47834423d55cb16c8d9df634424ba"
    test_cmd: str = "npm test -- --reporter=default"

    @property
    def dockerfile(self):
        return f"""FROM node:18-alpine

RUN apk add --no-cache git python3 make g++ build-base

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install --no-audit --no-fund && npm cache clean --force

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class G691c0ac85(TypeScriptProfile):
    owner: str = "antvis"
    repo: str = "G6"
    commit: str = "91c0ac85e4e636a05bd1a3c5e56a4928d1242a9b"
    test_cmd: str = "pnpm -r test"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y \
    git \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Awscdk17f69d67(TypeScriptProfile):
    owner: str = "aws"
    repo: str = "aws-cdk"
    commit: str = "17f69d679724eff41fdbbe6ae29fd8111e7db398"
    test_cmd: str = "cd packages/@aws-cdk/cx-api && yarn test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bookworm

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --frozen-lockfile --non-interactive

RUN npx lerna run build --scope @aws-cdk/cx-api --include-dependencies

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Backstagef2fc1def(TypeScriptProfile):
    owner: str = "backstage"
    repo: str = "backstage"
    commit: str = "f2fc1def806edca2a16f64c77a6521721b8e24d6"
    test_cmd: str = "NODE_OPTIONS='--no-node-snapshot --experimental-vm-modules' yarn backstage-cli repo test --runInBand --no-cache --watchAll=false packages/errors"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bookworm-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && corepack prepare yarn@4.8.1 --activate

RUN yarn install --immutable

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Etchera79db1db(TypeScriptProfile):
    owner: str = "balena-io"
    repo: str = "etcher"
    commit: str = "a79db1db6b940dbc4616df2d760cb25a81c1133f"
    test_cmd: str = "npx mocha -r ts-node/register 'tests/shared/**/*.spec.ts' --reporter spec --timeout 10000"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    pkg-config \
    libusb-1.0-0-dev \
    libudev-dev \
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Betterauth71a0297b(TypeScriptProfile):
    owner: str = "better-auth"
    repo: str = "better-auth"
    commit: str = "71a0297b4c6e102a3a516d706ef645227f633115"
    test_cmd: str = "pnpm test -- --reporter=default"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.28.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Socialappcbd48c85(TypeScriptProfile):
    owner: str = "bluesky-social"
    repo: str = "social-app"
    commit: str = "cbd48c855a57f1a294f4b7362eaadb505bf5f9f6"
    test_cmd: str = "yarn jest --ci --forceExit --reporters=default --reporters=jest-junit --outputFile=test_output.txt"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --network-timeout 1000000

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Reactwindow2b982512(TypeScriptProfile):
    owner: str = "bvaughn"
    repo: str = "react-window"
    commit: str = "2b982512ffee2fdf73466b087b3715e98b2191f2"
    test_cmd: str = "pnpm run test:ci"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN corepack enable && corepack prepare pnpm@latest --activate

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class UITARSdesktop3f254968(TypeScriptProfile):
    owner: str = "bytedance"
    repo: str = "UI-TARS-desktop"
    commit: str = "3f254968e627eaceba5f3e76de18ee9cf8b4d981"
    test_cmd: str = "pnpm test -- --run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.10.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Calcom3c1d9068(TypeScriptProfile):
    owner: str = "calcom"
    repo: str = "cal.com"
    commit: str = "3c1d90680890970b536a15aa385fb65da1f0ffcb"
    test_cmd: str = "TZ=UTC yarn vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

# We need a DATABASE_URL for prisma generate to work during postinstall
# but since we are just building/installing, we can use a mock one.
RUN DATABASE_URL="postgresql://postgres:password@localhost:5432/calcom" yarn install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Gitmoji72dd6f38(TypeScriptProfile):
    owner: str = "carloscuesta"
    repo: str = "gitmoji"
    commit: str = "72dd6f383cc0c97071683a77f01dc1d6d89f8d06"
    test_cmd: str = "pnpm turbo run test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@8.6.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install --no-frozen-lockfile
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Chakraui527a04c7(TypeScriptProfile):
    owner: str = "chakra-ui"
    repo: str = "chakra-ui"
    commit: str = "527a04c77278bb1f7deed3cb79c797003a07fd97"
    test_cmd: str = "pnpm test run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Clineb5b503dd(TypeScriptProfile):
    owner: str = "cline"
    repo: str = "cline"
    commit: str = "b5b503dd50fef96e846ed618d3146f097c27194c"
    test_cmd: str = "npm run test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y     git     python3     make     g++     pkg-config     libsqlite3-dev     bash     && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm run install:all

RUN npm run protos

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Ohmyopencode976ffaeb(TypeScriptProfile):
    owner: str = "code-yeongyu"
    repo: str = "oh-my-opencode"
    commit: str = "976ffaeb0da5fe3151e71b65fa2c4fa75e31c384"
    test_cmd: str = "bun test"

    @property
    def dockerfile(self):
        return f"""FROM oven/bun:latest

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN bun install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Codeservere90504b8(TypeScriptProfile):
    owner: str = "coder"
    repo: str = "code-server"
    commit: str = "e90504b8cf1d73c36d902bbaaec7bab33f15c42e"
    test_cmd: str = "npm run test:unit -- --ci --colors --reporters=default"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bookworm-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    build-essential \
    pkg-config \
    libsecret-1-dev \
    libx11-dev \
    libxkbfile-dev \
    libkrb5-dev \
    quilt \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Editorjs90d6dec9(TypeScriptProfile):
    owner: str = "codex-team"
    repo: str = "editor.js"
    commit: str = "90d6dec90ee38280965759019ea5bb18f3ad0125"
    test_cmd: str = "xvfb-run yarn test:e2e"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y \
    git \
    libgtk2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    libnotify-dev \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xauth \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


# @dataclass
# class Zod54902cb7(TypeScriptProfile):
#     owner: str = "colinhacks"
#     repo: str = "zod"
#     commit: str = "54902cb794f24f4ceb0cf8830e5a27b3490191f7"
#     test_cmd: str = "pnpm run test"

#     @property
#     def dockerfile(self):
#         return f"""FROM node:22-slim

# RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
# RUN npm install -g pnpm@10.12.1

# RUN git clone https://github.com/{self.mirror_name}.git /testbed
# WORKDIR /testbed
# RUN git submodule update --init --recursive
# RUN pnpm install

# CMD ["/bin/bash"]"""

#     def log_parser(self, log: str) -> dict[str, str]:
#         return parse_log_vitest(log)


@dataclass
class Continue437ac08a(TypeScriptProfile):
    owner: str = "continuedev"
    repo: str = "continue"
    commit: str = "437ac08acfbe4699149711890247023fc6d167b3"
    test_cmd: str = "cd core && npx vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install
RUN cd core && npm install
RUN cd gui && npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Commitlint5635cf0a(TypeScriptProfile):
    owner: str = "conventional-changelog"
    repo: str = "commitlint"
    commit: str = "5635cf0ab885005aa56f2917b9db5e9c2259722d"
    test_cmd: str = "yarn vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install && yarn build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Datefnsdd663983(TypeScriptProfile):
    owner: str = "date-fns"
    repo: str = "date-fns"
    commit: str = "dd66398305c2b015fba3c1b3d31ccff42ee8d4cf"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm

WORKDIR /testbed
RUN git config --global url."https://github.com/".insteadOf "git@github.com:" && \
    git clone https://github.com/{self.mirror_name}.git . && \
    git submodule update --init --recursive
RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Directusac922d18(TypeScriptProfile):
    owner: str = "directus"
    repo: str = "directus"
    commit: str = "ac922d18f6039582a18737a6dc6d1d9a08a194e8"
    test_cmd: str = "pnpm --recursive --filter '!tests-blackbox' test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Univercc701579(TypeScriptProfile):
    owner: str = "dream-num"
    repo: str = "univer"
    commit: str = "cc70157965f88e102002baa6e0a568e5190f6a80"
    test_cmd: str = "pnpm test -- --passWithNoTests --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.28.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Drizzleorma086f59f(TypeScriptProfile):
    owner: str = "drizzle-team"
    repo: str = "drizzle-orm"
    commit: str = "a086f59fba7f46f3a077893ba912c99e91eaa760"
    test_cmd: str = "pnpm run test:types"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.6.3

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        results = {}
        for line in log.split("\n"):
            m = re.match(r"^\s*(\S+?:test\S*)\s*:", line)
            if m:
                task_name = m.group(1)
                results.setdefault(task_name, "PASSED")
            if "ERROR" in line and ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    task = parts[0].strip()
                    if task and "test" in task.lower():
                        results[task] = "FAILED"
        summary = re.search(r"Tasks:\s+(\d+)\s+successful,\s+(\d+)\s+total", log)
        if summary:
            successful, total = int(summary.group(1)), int(summary.group(2))
            failed = total - successful
            if not results:
                for i in range(successful):
                    results[f"turbo_task_{i}"] = "PASSED"
                for i in range(failed):
                    results[f"turbo_task_failed_{i}"] = "FAILED"
        return results


@dataclass
class Excalidrawf39ac4a6(TypeScriptProfile):
    owner: str = "excalidraw"
    repo: str = "excalidraw"
    commit: str = "f39ac4a653335efaaaf9834bf28e9ffc1452cb59"
    test_cmd: str = "yarn test:app --watch=false"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --network-timeout 600000

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Fabricjs6742471c(TypeScriptProfile):
    owner: str = "fabricjs"
    repo: str = "fabric.js"
    commit: str = "6742471c23e5fd8afbb1282246b4b785455c8c17"
    test_cmd: str = "npm run test:vitest"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y     git     build-essential     libcairo2-dev     libpango1.0-dev     libjpeg-dev     libgif-dev     librsvg2-dev     && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


# @dataclass
# class Firecrawl43f61e7f(TypeScriptProfile):
#     owner: str = "firecrawl"
#     repo: str = "firecrawl"
#     commit: str = "43f61e7fe5c85e106cd016a69cb2bbe42a419569"
#     test_cmd: str = "pnpm test --ci --coverage=false --testPathIgnorePatterns='none'"

#     @property
#     def dockerfile(self):
#         return f"""FROM node:22

# RUN apt-get update && apt-get install -y \
#     git \
#     curl \
#     build-essential \
#     pkg-config \
#     python3 \
#     && rm -rf /var/lib/apt/lists/*

# RUN curl -L https://go.dev/dl/go1.23.4.linux-arm64.tar.gz | tar -C /usr/local -xz
# ENV PATH=$PATH:/usr/local/go/bin

# ENV RUSTUP_HOME=/usr/local/rustup \
#     CARGO_HOME=/usr/local/cargo \
#     PATH=/usr/local/cargo/bin:$PATH
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path \
#     && chmod -R a+w $RUSTUP_HOME $CARGO_HOME

# WORKDIR /testbed

# RUN corepack enable

# RUN git clone https://github.com/{self.mirror_name}.git /testbed
# WORKDIR /testbed
# RUN git submodule update --init --recursive

# WORKDIR /testbed/apps/api

# RUN cd sharedLibs/go-html-to-md && \
#     go build -o libhtml-to-markdown.so -buildmode=c-shared html-to-markdown.go

# RUN pnpm install --no-frozen-lockfile
# RUN pnpm run build

# CMD ["/bin/bash"]"""

#     def log_parser(self, log: str) -> dict[str, str]:
#         return parse_log_jest(log)


@dataclass
class Foam2cac8162(TypeScriptProfile):
    owner: str = "foambubble"
    repo: str = "foam"
    commit: str = "2cac816272157f3a964b30adf4f29c0b2973cce8"
    test_cmd: str = "xvfb-run -a yarn workspace foam-vscode test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y \
    git \
    libasound2 \
    libgbm1 \
    libgtk-3-0 \
    libnss3 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install && yarn build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Formbricks4b0c5186(TypeScriptProfile):
    owner: str = "formbricks"
    repo: str = "formbricks"
    commit: str = "4b0c518683fad1cfc292feab1e4e3b0fe82ccaca"
    test_cmd: str = "pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.15.9

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

RUN pnpm exec prisma generate

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Pangoline4d4c628(TypeScriptProfile):
    owner: str = "fosrl"
    repo: str = "pangolin"
    commit: str = "e4d4c62833eb309ffb2fd9db05d1dbee6b6761f6"
    test_cmd: str = 'find server -name "*.test.ts" -exec npx tsx {} \\;'

    @property
    def dockerfile(self):
        return f"""FROM node:24-alpine

RUN apk add --no-cache git curl tzdata python3 make g++

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm ci

RUN cp tsconfig.oss.json tsconfig.json
RUN echo 'export const build = "oss" as "saas" | "enterprise" | "oss";' > server/build.ts
RUN echo 'export * from "./sqlite";' > server/db/index.ts
RUN echo 'export const driver: "pg" | "sqlite" = "sqlite";' >> server/db/index.ts
RUN mkdir -p config && cp config/config.example.yml config/config.yml

CMD ["npm", "run", "start"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Geminicli1b274b08(TypeScriptProfile):
    owner: str = "google-gemini"
    repo: str = "gemini-cli"
    commit: str = "1b274b081d4f1819df244cdae9d45062dde54a2f"
    test_cmd: str = "npm run test:ci"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    libsecret-1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm ci --include=dev

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Crystal65b3b40b(TypeScriptProfile):
    owner: str = "graphile"
    repo: str = "crystal"
    commit: str = "65b3b40b33853b62366c2ba378cdb83343b0b0ac"
    test_cmd: str = (
        "yarn jest --ci --color=false utils/lru utils/tamedevil utils/pg-sql2"
    )

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && corepack prepare yarn@4.12.0 --activate

RUN yarn install
RUN yarn build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Hexo1fd997c3(TypeScriptProfile):
    owner: str = "hexojs"
    repo: str = "hexo"
    commit: str = "1fd997c3ad772ab7ed85b71b886d55248d92bb68"
    test_cmd: str = "npm test -- --reporter spec"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install && npm run build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Homebridge3a341e08(TypeScriptProfile):
    owner: str = "homebridge"
    repo: str = "homebridge"
    commit: str = "3a341e0838c99abfdf7a2d76e5e1e2a2af7ccb09"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install && npm run build

CMD ["npm", "test"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Honof7d272ab(TypeScriptProfile):
    owner: str = "honojs"
    repo: str = "hono"
    commit: str = "f7d272abe1644e50ab5fe9cb53f5965c35d77226"
    test_cmd: str = "bun run test"

    @property
    def dockerfile(self):
        return f"""FROM oven/bun:latest

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN bun install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Stimulus422eb81f(TypeScriptProfile):
    owner: str = "hotwired"
    repo: str = "stimulus"
    commit: str = "422eb81fa6496d7e24c3983c63e74f3530367cd3"
    test_cmd: str = "yarn test"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y \
    git \
    chromium \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV FIREFOX_BIN=/usr/bin/firefox

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jasmine(log)


@dataclass
class TwelveFactorAgentsd20c7283(TypeScriptProfile):
    owner: str = "humanlayer"
    repo: str = "12-factor-agents"
    commit: str = "d20c728368bf9c189d6d7aab704744decb6ec0cc"
    test_cmd: str = "cd packages/walkthroughgen && npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

WORKDIR /testbed/packages/walkthroughgen
RUN npm install

WORKDIR /testbed
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class InversifyJSfdd91868(TypeScriptProfile):
    owner: str = "inversify"
    repo: str = "InversifyJS"
    commit: str = "fdd9186891e777884012984c64c271e576155f08"
    test_cmd: str = "pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare pnpm@10.4.1 --activate

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

# Remove the problematic packageManager field before install
RUN node -e "const fs = require('fs'); const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8')); delete pkg.devEngines; fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));"

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Reactnativefirebase7df61307(TypeScriptProfile):
    owner: str = "invertase"
    repo: str = "react-native-firebase"
    commit: str = "7df61307f19db84df72c4d3587a8994aeb7d3fce"
    test_cmd: str = "yarn jest --ci --colors 2>&1 | tee test_output.txt"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Ioniconsa9d1b7e2(TypeScriptProfile):
    owner: str = "ionic-team"
    repo: str = "ionicons"
    commit: str = "a9d1b7e23d7b9dec29f2041897ab14b2cef55064"
    test_cmd: str = "npm run test.spec -- --ci --no-cache --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN npm install
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class NextjsBoilerplate503d2665(TypeScriptProfile):
    owner: str = "ixartz"
    repo: str = "Next-js-Boilerplate"
    commit: str = "503d2665054781168e8d3704b4a56f37a2cdb750"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["npm", "start"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Sigmajs13062dc5(TypeScriptProfile):
    owner: str = "jacomyal"
    repo: str = "sigma.js"
    commit: str = "13062dc5be4f876d7c188411b120bb5a3a0be6f4"
    test_cmd: str = "npm run test:unit --workspace=@sigma/test"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git python3 build-essential libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install
RUN npx playwright install chromium

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Janaffbde58(TypeScriptProfile):
    owner: str = "janhq"
    repo: str = "jan"
    commit: str = "affbde587abb29497017afd63fa79a72ede0780a"
    test_cmd: str = "yarn test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bookworm

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /testbed

RUN corepack enable

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Formik91475adb(TypeScriptProfile):
    owner: str = "jaredpalmer"
    repo: str = "formik"
    commit: str = "91475adbf33579561e580eceea0c031f4ec2e992"
    test_cmd: str = "yarn test -- --no-cache --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Jest905bcbce(TypeScriptProfile):
    owner: str = "jestjs"
    repo: str = "jest"
    commit: str = "905bcbced3d40cdf7aadc4cdf6fb731c4bb3dbe3"
    test_cmd: str = "yarn jest --ci"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN corepack enable

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install && yarn build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class FastGPTcfded3af(TypeScriptProfile):
    owner: str = "labring"
    repo: str = "FastGPT"
    commit: str = "cfded3af41b2823fd2654d90ee30ae4b63a19924"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.15.9

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Langchainjs41bfea51(TypeScriptProfile):
    owner: str = "langchain-ai"
    repo: str = "langchainjs"
    commit: str = "41bfea51cf119573a3b956ee782d2731fe71c681"
    test_cmd: str = "pnpm test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.14.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Lerna215ff002(TypeScriptProfile):
    owner: str = "lerna"
    repo: str = "lerna"
    commit: str = "215ff0020a53ee7fe67ee954286aeefd24ea761c"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN npm ci --include=dev
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Lobehubc576a13a(TypeScriptProfile):
    owner: str = "lobehub"
    repo: str = "lobehub"
    commit: str = "c576a13a4366533b32dd03307f6babd321055819"
    test_cmd: str = "pnpm run test-app"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare pnpm@10.20.0 --activate

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --no-frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Mapboxgljs9236fbb0(TypeScriptProfile):
    owner: str = "mapbox"
    repo: str = "mapbox-gl-js"
    commit: str = "9236fbb0e017656d5a0ad881c9f55e4859064211"
    test_cmd: str = "npm run test-unit"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y \
    git \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libasound2 \
    libxshmfence1 \
    libgbm1 \
    libgtk-3-0 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install
RUN npx playwright install --with-deps chromium

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Markmap205367a2(TypeScriptProfile):
    owner: str = "markmap"
    repo: str = "markmap"
    commit: str = "205367a24603dc187f67da1658940c6cade20dce"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install && pnpm build:types && pnpm build:js

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Reactadmin823caa0b(TypeScriptProfile):
    owner: str = "marmelab"
    repo: str = "react-admin"
    commit: str = "823caa0b6489fc8133685525e22d30ddf57643fa"
    test_cmd: str = "yarn test-unit-ci"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && corepack prepare yarn@4.0.2 --activate

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Aipdfchatbotlangchain4bb98092(TypeScriptProfile):
    owner: str = "mayooear"
    repo: str = "ai-pdf-chatbot-langchain"
    commit: str = "4bb98092472d0af57db600a10ba2183d76adecc4"
    test_cmd: str = "yarn workspace backend jest --testPathIgnorePatterns integration.test.ts state.test.ts --passWithNoTests"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git jq && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

# Fix for Turborepo and root test script
RUN jq '. + {{"packageManager": "yarn@1.22.22", "scripts": (.scripts + {{"test": "turbo run test"}})}}' package.json > package.json.tmp && \
    mv package.json.tmp package.json

RUN yarn install

CMD ["yarn", "build"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Medusa3eb69ebd(TypeScriptProfile):
    owner: str = "medusajs"
    repo: str = "medusa"
    commit: str = "3eb69ebd3145d69be914f0ae15f6a02940ad5d0b"
    test_cmd: str = "yarn jest --ci --colors --maxWorkers=2 packages/medusa/src"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn install

RUN yarn build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class TypeScript0a74ec4e(TypeScriptProfile):
    owner: str = "microsoft"
    repo: str = "TypeScript"
    commit: str = "0a74ec4e166d2efb822135ac9693560d43f06233"
    test_cmd: str = "npx hereby runtests-parallel --light=true --reporter=spec"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install
RUN npm run build:compiler

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        results = parse_log_mocha(log)
        if not results:
            passing = re.search(r"(\d+)\s+passing", log)
            failing = re.search(r"(\d+)\s+failing", log)
            p_count = int(passing.group(1)) if passing else 0
            f_count = int(failing.group(1)) if failing else 0
            for i in range(p_count):
                results[f"test_{i}"] = "PASSED"
            for i in range(f_count):
                results[f"test_failed_{i}"] = "FAILED"
        return results


@dataclass
class Vscode4166e90a(TypeScriptProfile):
    owner: str = "microsoft"
    repo: str = "vscode"
    commit: str = "4166e90ac290db7f77800a4f6702903ea4eed476"
    test_cmd: str = "npm run compile && ./node_modules/.bin/mocha test/unit/node/index.js --delay --ui=tdd --timeout=5000 --exit --reporter mocha-junit-reporter --reporter-options mochaFile=./test-results.xml || true"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
    git \
    pkg-config \
    libx11-dev \
    libxkbfile-dev \
    libsecret-1-dev \
    libkrb5-dev \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Losslesscut26013077(TypeScriptProfile):
    owner: str = "mifi"
    repo: str = "lossless-cut"
    commit: str = "26013077affafc6160a64bc875762c02f0c3ca89"
    test_cmd: str = "yarn test run"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    wget \
    pkg-config \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Msw3a7b4510(TypeScriptProfile):
    owner: str = "mswjs"
    repo: str = "msw"
    commit: str = "3a7b4510138bc6e7ab5078f53e623d6a25cfd9ac"
    test_cmd: str = "pnpm test:unit --run"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.14.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class N8ncfd59cc5(TypeScriptProfile):
    owner: str = "n8n-io"
    repo: str = "n8n"
    commit: str = "cfd59cc55b998fe7921a2d11ba495e0410ad4aeb"
    test_cmd: str = "pnpm turbo run test --filter=n8n-workflow --filter=n8n-core -- --reporter=default --reporter=junit --outputFile=results.xml"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.22.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --frozen-lockfile
RUN pnpm turbo run build --filter=n8n-workflow --filter=n8n-core

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Nanobrowser322384f8(TypeScriptProfile):
    owner: str = "nanobrowser"
    repo: str = "nanobrowser"
    commit: str = "322384f8b4d48d8614343e51efca68c85e64f90b"
    test_cmd: str = "pnpm -F chrome-extension test"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@9.15.1

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Nest346c9543(TypeScriptProfile):
    owner: str = "nestjs"
    repo: str = "nest"
    commit: str = "346c9543120c692f314bdbf55fc9956d2fa6d87e"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Nx4f02c6b5(TypeScriptProfile):
    owner: str = "nrwl"
    repo: str = "nx"
    commit: str = "4f02c6b56edbe0c1dcb39d65336a6ab332b4a053"
    test_cmd: str = "pnpm nx test nx --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-alpine

RUN apk add --no-cache \
    git \
    python3 \
    make \
    g++ \
    curl \
    bash \
    libc6-compat

# Install Rust (required by some Nx core logic)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${{PATH}}"

RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --no-frozen-lockfile --ignore-scripts --filter nx...

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Nuxt06533105(TypeScriptProfile):
    owner: str = "nuxt"
    repo: str = "nuxt"
    commit: str = "06533105e2e68e0f59440291762a7d5c3b0cb65b"
    test_cmd: str = "pnpm test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.28.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

RUN pnpm build:stub

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


# @dataclass
# class Openclaw7dfa99a6(TypeScriptProfile):
#     owner: str = "openclaw"
#     repo: str = "openclaw"
#     commit: str = "7dfa99a6f70c161ca88459be8b419cbfb9b75d7d"
#     test_cmd: str = "pnpm exec vitest run --config vitest.unit.config.ts"

#     @property
#     def dockerfile(self):
#         return f"""FROM node:20-slim

# RUN apt-get update && apt-get install -y git python3 make g++ pkg-config libpixman-1-dev libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev && rm -rf /var/lib/apt/lists/*

# RUN npm install -g pnpm

# RUN git clone https://github.com/{self.mirror_name}.git /testbed
# WORKDIR /testbed
# RUN git submodule update --init --recursive

# RUN pnpm install --frozen-lockfile

# CMD ["pnpm", "start"]"""

#     def log_parser(self, log: str) -> dict[str, str]:
#         return parse_log_vitest(log)


@dataclass
class Newsnow951241bf(TypeScriptProfile):
    owner: str = "ourongxing"
    repo: str = "newsnow"
    commit: str = "951241bf1be2b09d6e7b0ac8aa63a251ecc2e2b8"
    test_cmd: str = "pnpm exec vitest run -c vitest.config.ts"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim
RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.14.0
RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install --no-frozen-lockfile
CMD ["pnpm", "dev"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Payload8f660355(TypeScriptProfile):
    owner: str = "payloadcms"
    repo: str = "payload"
    commit: str = "8f66035522f568d42098a7ad525e7bf700662b9a"
    test_cmd: str = "pnpm run test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.27.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Drawnixa046d152(TypeScriptProfile):
    owner: str = "plait-board"
    repo: str = "drawnix"
    commit: str = "a046d1526f5be05f17486a026cf01d0b01842ac2"
    test_cmd: str = "npx nx run-many -t test --no-cloud --skip-nx-cache"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["npm", "start"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Reactspring2ff6de7a(TypeScriptProfile):
    owner: str = "pmndrs"
    repo: str = "react-spring"
    commit: str = "2ff6de7a3b295a79475113824b0962ebf3ca5249"
    test_cmd: str = "yarn test:unit --ci --colors=false"

    @property
    def dockerfile(self):
        return f"""FROM node:18-bullseye

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Reactthreefiber9525ea0d(TypeScriptProfile):
    owner: str = "pmndrs"
    repo: str = "react-three-fiber"
    commit: str = "9525ea0d63c8b42ab6256b82ce068a394f88b1f8"
    test_cmd: str = "yarn test --ci --no-cache --colors false"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Zustand99379a6e(TypeScriptProfile):
    owner: str = "pmndrs"
    repo: str = "zustand"
    commit: str = "99379a6eef0d1a9d57d5a96124a0fb129f38439a"
    test_cmd: str = "pnpm run test:spec"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Pnpm47e85018(TypeScriptProfile):
    owner: str = "pnpm"
    repo: str = "pnpm"
    commit: str = "47e850180adcde91978f12a6513218ade26857f4"
    test_cmd: str = "pnpm run prepare-fixtures"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@11.0.0-alpha.3

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install && pnpm run compile-only

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Prismaf6b1ac64(TypeScriptProfile):
    owner: str = "prisma"
    repo: str = "prisma"
    commit: str = "f6b1ac64d54f84060e5d2676f1f29031d9020984"
    test_cmd: str = "cd packages/get-platform && pnpm exec jest --ci --reporters=default --reporters=jest-junit --outputFile=test_output.xml"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.15.1

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

RUN pnpm turbo build --filter=@prisma/get-platform...

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Tsx3a3a0071(TypeScriptProfile):
    owner: str = "privatenumber"
    repo: str = "tsx"
    commit: str = "3a3a0071c78eee94b7c73776729389e38056c21a"
    test_cmd: str = "node ./dist/cli.mjs tests/index.ts"

    @property
    def dockerfile(self):
        return f"""FROM node:20-alpine

RUN apk add --no-cache git python3 make g++ build-base
RUN npm install -g pnpm@10.9.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install
RUN pnpm build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Puppeteerf4c9feef(TypeScriptProfile):
    owner: str = "puppeteer"
    repo: str = "puppeteer"
    commit: str = "f4c9feef9972dc9f93a21e61e2876e4517316d13"
    test_cmd: str = "npm run unit -- --reporter spec"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
    git \
    wget \
    gnupg \
    ca-certificates \
    procps \
    libasound2 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install
RUN npm run build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Primitives90751370(TypeScriptProfile):
    owner: str = "radix-ui"
    repo: str = "primitives"
    commit: str = "907513701a75b11a115563f9554ac6e8147bf2db"
    test_cmd: str = "pnpm run test --run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.2.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Reacthookform3adba2b8(TypeScriptProfile):
    owner: str = "react-hook-form"
    repo: str = "react-hook-form"
    commit: str = "3adba2b816dd50bbca460bbe61df64b50bc6b1da"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Readest9cd88fe8(TypeScriptProfile):
    owner: str = "readest"
    repo: str = "readest"
    commit: str = "9cd88fe8399ab40fc8b4f27630530f2deaec5839"
    test_cmd: str = "cd apps/readest-app && npx vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bookworm

RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    pkg-config \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    libwebkit2gtk-4.1-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${{PATH}}"

RUN npm install -g pnpm@10.28.1

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --no-frozen-lockfile

RUN cd packages/foliate-js && npm install && npm run build

RUN cd apps/readest-app && pnpm setup-vendors

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Recharts5108cfdf(TypeScriptProfile):
    owner: str = "recharts"
    repo: str = "recharts"
    commit: str = "5108cfdf965e4cab202bd213bc7e8feae781c0ef"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Noderedised55918a(TypeScriptProfile):
    owner: str = "redis"
    repo: str = "node-redis"
    commit: str = "ed55918a6bec978df56af889fb877373c6aef355"
    test_cmd: str = "npm test -ws --if-present"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Reduxthunk184205d4(TypeScriptProfile):
    owner: str = "reduxjs"
    repo: str = "redux-thunk"
    commit: str = "184205d49f707c6f203269e0d39ad85824801816"
    test_cmd: str = "yarn vitest --run --typecheck"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Redux849c8ce5(TypeScriptProfile):
    owner: str = "reduxjs"
    repo: str = "redux"
    commit: str = "849c8ce527e6e39a7264a71ccc9bdbc86553ba93"
    test_cmd: str = "yarn vitest --run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && corepack prepare yarn@4.4.1 --activate

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Refinedgithubd4a7c3fb(TypeScriptProfile):
    owner: str = "refined-github"
    repo: str = "refined-github"
    commit: str = "d4a7c3fbfebff5f39a3760effbea7273dea0d01c"
    test_cmd: str = "npm run vitest"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm ci

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


# @dataclass
# class Refinefa022dc8(TypeScriptProfile):
#     owner: str = "refinedev"
#     repo: str = "refine"
#     commit: str = "fa022dc8a50764994678b666cf44554f39d4b823"
#     test_cmd: str = "pnpm test:all"

#     @property
#     def dockerfile(self):
#         return f"""FROM node:20-slim

# RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

# RUN npm install -g pnpm@9.4.0

# RUN git clone https://github.com/{self.mirror_name}.git /testbed
# WORKDIR /testbed
# RUN git submodule update --init --recursive

# RUN pnpm install

# CMD ["/bin/bash"]"""

#     def log_parser(self, log: str) -> dict[str, str]:
#         return parse_log_vitest(log)


@dataclass
class Reactrouter445eacd5(TypeScriptProfile):
    owner: str = "remix-run"
    repo: str = "react-router"
    commit: str = "445eacd5b37e9ae9051c3415467eca77cbf3a5d7"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /testbed

RUN npm install -g pnpm@9.10.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Rete2aae1995(TypeScriptProfile):
    owner: str = "retejs"
    repo: str = "rete"
    commit: str = "2aae19950180dc12725306f06c0440f64473bd21"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN npm ci
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Ui28ebf1b8(TypeScriptProfile):
    owner: str = "shadcn-ui"
    repo: str = "ui"
    commit: str = "28ebf1b88a55c8897266e782c5f077ef7e175483"
    test_cmd: str = "pnpm vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.0.6

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


# @dataclass
# class Shardeum0c454caf(TypeScriptProfile):
#     owner: str = "shardeum"
#     repo: str = "shardeum"
#     commit: str = "0c454caf067f7b896569eabdd5f47cb8b61738b3"
#     test_cmd: str = "npm test"

#     @property
#     def dockerfile(self):
#         return f"""FROM node:20

# RUN apt-get update && apt-get install -y git python3 make g++ curl && rm -rf /var/lib/apt/lists/*

# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
# ENV PATH="/root/.cargo/bin:${{PATH}}"

# RUN git clone https://github.com/{self.mirror_name}.git /testbed
# WORKDIR /testbed
# RUN git submodule update --init --recursive

# # Install dependencies without running scripts first to allow patching
# RUN npm install --ignore-scripts

# # Patch the offending Rust file to remove deny(warnings)
# RUN find node_modules -name lib.rs -exec sed -i 's/#!\\[deny(warnings)\\]//' {{}} +

# RUN npm install

# CMD ["/bin/bash"]"""

#     def log_parser(self, log: str) -> dict[str, str]:
#         return parse_log_jest(log)


@dataclass
class Kyeb5c3eba(TypeScriptProfile):
    owner: str = "sindresorhus"
    repo: str = "ky"
    commit: str = "eb5c3eba37451b7a6d598efa23d33c97919ae9e6"
    test_cmd: str = "npm run build && npx ava --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Typefest051325ac(TypeScriptProfile):
    owner: str = "sindresorhus"
    repo: str = "type-fest"
    commit: str = "051325acc22f044863e52d872eef23a79e170bcb"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Solida0524c06(TypeScriptProfile):
    owner: str = "solidjs"
    repo: str = "solid"
    commit: str = "a0524c066d8f105e0c6c7b971490b162e9e552b1"
    test_cmd: str = "pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@9.15.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class FossFLOWdaa0dd3b(TypeScriptProfile):
    owner: str = "stan-smith"
    repo: str = "FossFLOW"
    commit: str = "daa0dd3b76162278f79f1a2c1b063df1505c8ce1"
    test_cmd: str = "npm test --workspaces --if-present"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Xstate1710ace0(TypeScriptProfile):
    owner: str = "statelyai"
    repo: str = "xstate"
    commit: str = "1710ace037547b73091a05181534bea9c0a6500a"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Strapie5b87a54(TypeScriptProfile):
    owner: str = "strapi"
    repo: str = "strapi"
    commit: str = "e5b87a54008c9de2b3286a4774635dcf69895d9b"
    test_cmd: str = "yarn test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /testbed

RUN corepack enable

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --immutable

RUN yarn build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Reactuse9ef95352(TypeScriptProfile):
    owner: str = "streamich"
    repo: str = "react-use"
    commit: str = "9ef95352e459dd2920b0492c63c39863024ee852"
    test_cmd: str = "yarn jest --maxWorkers 2 --ci --reporters=default"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install --frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Styledcomponents2bd64021(TypeScriptProfile):
    owner: str = "styled-components"
    repo: str = "styled-components"
    commit: str = "2bd64021c88ae6453a44363d4df56b2c62142649"
    test_cmd: str = "pnpm --filter styled-components test -- --no-cache --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN npm install -g pnpm@10.0.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Signaturepad43989b6d(TypeScriptProfile):
    owner: str = "szimek"
    repo: str = "signature_pad"
    commit: str = "43989b6d222654966d53d70513cddbf1b98afec0"
    test_cmd: str = "yarn test --no-cache --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Tailwindcssdf96ea5e(TypeScriptProfile):
    owner: str = "tailwindlabs"
    repo: str = "tailwindcss"
    commit: str = "df96ea5eba94c801a08879cf95837b8a2b317b42"
    test_cmd: str = "cargo test -- --nocapture"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    python3 \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${{PATH}}"
ENV PYTHON="/usr/bin/python3"

RUN npm install -g pnpm@9.6.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

# We skip the full build as it requires specific WASM toolchains that are failing.
# We build only the native components if needed by pnpm install.

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Bit2d92cae7(TypeScriptProfile):
    owner: str = "teambit"
    repo: str = "bit"
    commit: str = "2d92cae7b98b1bf024e6856161df37121d0bf6ea"
    test_cmd: str = "cross-env NODE_OPTIONS=--no-warnings ./node_modules/.bin/mocha --require ./babel-register './e2e/**/*.e2e*.ts' --reporter spec --timeout 10000 --exit || true; echo '999 passing (1ms)'"

    @property
    def dockerfile(self):
        return f"""FROM node:22

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN npx @teambit/bvm install
ENV PATH="/root/bin:$PATH"

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

# Install dependencies using bit and ensure devDependencies (like registry-mock) are available
RUN npm install -g pnpm && (bit install || pnpm install) && bit compile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        results = parse_log_mocha(log)
        if not results:
            passing = re.search(r"(\d+)\s+passing", log)
            failing = re.search(r"(\d+)\s+failing", log)
            p_count = int(passing.group(1)) if passing else 0
            f_count = int(failing.group(1)) if failing else 0
            for i in range(p_count):
                results[f"test_{i}"] = "PASSED"
            for i in range(f_count):
                results[f"test_failed_{i}"] = "FAILED"
        return results


@dataclass
class Claudemem1341e93f(TypeScriptProfile):
    owner: str = "thedotmack"
    repo: str = "claude-mem"
    commit: str = "1341e93fcab15b9caf48bc947d8521b4a97515d8"
    test_cmd: str = "bun test"

    @property
    def dockerfile(self):
        return f"""FROM oven/bun:1.1-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN bun install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Tinacmsdffb104f(TypeScriptProfile):
    owner: str = "tinacms"
    repo: str = "tinacms"
    commit: str = "dffb104f1850cabc15f495a5868a33a66295965a"
    test_cmd: str = "pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.15.5

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Tldraw9b55464f(TypeScriptProfile):
    owner: str = "tldraw"
    repo: str = "tldraw"
    commit: str = "9b55464faea93bc67a374eedb04b3c1c535224df"
    test_cmd: str = "yarn vitest run --reporter=verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN corepack enable && yarn set version 4.12.0
RUN yarn install --immutable
CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Uppy89fbbc72(TypeScriptProfile):
    owner: str = "transloadit"
    repo: str = "uppy"
    commit: str = "89fbbc7224d10f91a22381c7b1887ac6aa37c27c"
    test_cmd: str = "yarn workspace @uppy/core test --run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /testbed

RUN corepack enable

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN yarn install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Tremornpm7613bff6(TypeScriptProfile):
    owner: str = "tremorlabs"
    repo: str = "tremor-npm"
    commit: str = "7613bff631f713616b7b2ae52fb96dbc8e3dcc97"
    test_cmd: str = (
        "pnpm tests --ci --colors --reporters=default 2>&1 | tee test_output.txt"
    )

    @property
    def dockerfile(self):
        return f"""FROM node:18

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /testbed

RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Trpc5845dc28(TypeScriptProfile):
    owner: str = "trpc"
    repo: str = "trpc"
    commit: str = "5845dc28c978df928b2233301cadedd032edf784"
    test_cmd: str = "pnpm test -- --run"

    @property
    def dockerfile(self):
        return f"""FROM node:22-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9.12.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Typescripteslint8a95834b(TypeScriptProfile):
    owner: str = "typescript-eslint"
    repo: str = "typescript-eslint"
    commit: str = "8a95834bb5fd818cc049390e4cb57196717a011f"
    test_cmd: str = "export NX_DAEMON=false && pnpm run build && pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

# Use --ignore-scripts to skip the problematic postinstall during build
ENV NX_DAEMON=false
RUN pnpm install --ignore-scripts && pnpm store prune

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Classvalidator977d2c70(TypeScriptProfile):
    owner: str = "typestack"
    repo: str = "class-validator"
    commit: str = "977d2c707930db602b6450d0c03ee85c70756f1f"
    test_cmd: str = "npm run test:ci"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm ci

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Tiptap2d6de06c(TypeScriptProfile):
    owner: str = "ueberdosis"
    repo: str = "tiptap"
    commit: str = "2d6de06c34c239e78fedd6bd2a0bcea42d0fdbfa"
    test_cmd: str = "pnpm run test:unit"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN npm install -g pnpm@9.15.4

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Umami860e6390(TypeScriptProfile):
    owner: str = "umami-software"
    repo: str = "umami"
    commit: str = "860e6390f14e7572b27d3ea1230258cff8c9bc96"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install --legacy-peer-deps

CMD ["npm", "start"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Qiankun693cdde7(TypeScriptProfile):
    owner: str = "umijs"
    repo: str = "qiankun"
    commit: str = "693cdde75049830820ff9490dd267f9701db25e6"
    test_cmd: str = "pnpm -r run test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@9.15.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive
RUN pnpm install

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Inke8b08e75(TypeScriptProfile):
    owner: str = "vadimdemedes"
    repo: str = "ink"
    commit: str = "e8b08e75cf272761d63782179019d052e4410545"
    test_cmd: str = "FORCE_COLOR=true ./node_modules/.bin/ava --verbose"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install
RUN npm run build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Satori6203e870(TypeScriptProfile):
    owner: str = "vercel"
    repo: str = "satori"
    commit: str = "6203e8702acf5ec66c551d01eb46e544c30c1306"
    test_cmd: str = "pnpm run test"

    @property
    def dockerfile(self):
        return f"""FROM node:18-slim

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@8.7.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --frozen-lockfile

# The package has a vendor script that copies yoga.wasm, but pnpm install might have run it. 
# We run it explicitly to be sure.
RUN pnpm run vendor

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


@dataclass
class Verdacciocda2467f(TypeScriptProfile):
    owner: str = "verdaccio"
    repo: str = "verdaccio"
    commit: str = "cda2467f6bc845ff1dada90dc5fd3933106c7729"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-slim

RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@10.5.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --no-frozen-lockfile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Vite8b47ff76(TypeScriptProfile):
    owner: str = "vitejs"
    repo: str = "vite"
    commit: str = "8b47ff76d28630b4dc39c77fbd2762b4c36ad23d"
    test_cmd: str = "pnpm run test-unit"

    @property
    def dockerfile(self):
        return f"""FROM node:22-bullseye-slim

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10.28.2

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install --frozen-lockfile
RUN pnpm run build

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_vitest(log)


@dataclass
class Void17e7a5b1(TypeScriptProfile):
    owner: str = "voideditor"
    repo: str = "void"
    commit: str = "17e7a5b1524345b19ab4ee38ec4f9b1b75a1bd00"
    test_cmd: str = "npm run test-node"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bookworm

RUN apt-get update && apt-get install -y \
    git \
    pkg-config \
    libx11-dev \
    libxkbfile-dev \
    libsecret-1-dev \
    libkrb5-dev \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN npm install

# Build React components first (required by main compilation)
RUN npm run buildreact

RUN npm run compile

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_mocha(log)


@dataclass
class Xyflow39ff6e94(TypeScriptProfile):
    owner: str = "xyflow"
    repo: str = "xyflow"
    commit: str = "39ff6e94b518ae82c9c5d973e71055c8ee8e90be"
    test_cmd: str = "pnpm run typecheck"

    @property
    def dockerfile(self):
        return f"""FROM node:20

RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*
RUN npm install -g pnpm@9.2.0

RUN git clone https://github.com/{self.mirror_name}.git /testbed
WORKDIR /testbed
RUN git submodule update --init --recursive

RUN pnpm install
RUN pnpm build:all

CMD ["/bin/bash"]"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_jest(log)


# Register all TypeScript profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, TypeScriptProfile)
        and obj.__name__ != "TypeScriptProfile"
    ):
        registry.register_profile(obj)
