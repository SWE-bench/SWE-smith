FROM apex_arena:base

RUN apt-get update && apt-get install -y git

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/miniconda3 && \
    rm /tmp/miniconda.sh && /opt/miniconda3/bin/conda init bash

# Add conda to PATH
ENV PATH="/opt/miniconda3/bin:$PATH"

# USER model
RUN git clone https://github.com/Instagram/MonkeyType.git /workdir/MonkeyType
RUN mkdir -p /workdir/patches
COPY patch.diff /workdir/patches
RUN cd /workdir/MonkeyType && git checkout 70c3acf62950be5dfb28743c7a719bfdecebcd84
RUN cd /workdir/MonkeyType && git apply /workdir/patches/patch.diff
RUN rm -rf /workdir/patches
# Remove git history so the model can't see the patch being applied
RUN rm -rf /workdir/MonkeyType/.git

# USER root
RUN mkdir -p /test
COPY build.sh /test/build.sh
COPY run_test.sh /workdir/run_test.sh
RUN chmod +x /test/build.sh
RUN chmod +x /workdir/run_test.sh
RUN cd /workdir/MonkeyType && /test/build.sh 