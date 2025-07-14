#!/bin/bash
set -euxo pipefail
cd /workdir/MonkeyType
# Initialize conda for the current shell session
eval "$(conda shell.bash hook)"
cat <<'EOF_59812759871' > swesmith_environment.yml
name: testbed
channels:
  - defaults
dependencies:
  - _libgcc_mutex=0.1=main
  - _openmp_mutex=5.1=1_gnu
  - bzip2=1.0.8=h5eee18b_6
  - ca-certificates=2025.2.25=h06a4308_0
  - expat=2.7.1=h6a678d5_0
  - ld_impl_linux-64=2.40=h12ee557_0
  - libffi=3.4.4=h6a678d5_1
  - libgcc-ng=11.2.0=h1234567_1
  - libgomp=11.2.0=h1234567_1
  - libstdcxx-ng=11.2.0=h1234567_1
  - libuuid=1.41.5=h5eee18b_0
  - libxcb=1.17.0=h9b100fa_0
  - ncurses=6.4=h6a678d5_0
  - openssl=3.0.16=h5eee18b_0
  - pip=25.1=pyhc872135_2
  - pthread-stubs=0.3=h0ce48e5_1
  - python=3.10.18=h1a3bd86_0
  - readline=8.2=h5eee18b_0
  - setuptools=78.1.1=py310h06a4308_0
  - sqlite=3.45.3=h5eee18b_0
  - tk=8.6.14=h993c535_1
  - tzdata=2025b=h04d1e81_0
  - wheel=0.45.1=py310h06a4308_0
  - xorg-libx11=1.8.12=h9b100fa_1
  - xorg-libxau=1.0.12=h9b100fa_0
  - xorg-libxdmcp=1.1.5=h9b100fa_0
  - xorg-xorgproto=2024.1=h5eee18b_1
  - xz=5.6.4=h5eee18b_1
  - zlib=1.2.13=h5eee18b_1
  - pip:
      - exceptiongroup==1.3.0
      - iniconfig==2.1.0
      - libcst==1.8.2
      - monkeytype==23.3.0
      - mypy-extensions==1.1.0
      - packaging==25.0
      - pluggy==1.6.0
      - pygments==2.19.2
      - pytest==8.4.1
      - pyyaml==6.0.2
      - tomli==2.2.1
      - typing-extensions==4.14.1
prefix: /opt/miniconda3/envs/testbed

EOF_59812759871
conda env create --file swesmith_environment.yml
conda activate testbed && conda install python=3.10 -y
rm swesmith_environment.yml
conda activate testbed
echo "Current environment: $CONDA_DEFAULT_ENV"
python -m pip install -e .


# Set up bash to automatically activate testbed environment
echo "source /opt/miniconda3/etc/profile.d/conda.sh" >> /root/.bashrc
echo "conda activate testbed" >> /root/.bashrc