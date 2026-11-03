# Ubuntu 22.04 is in the upstream Legolas tested OS range.
# Platform is intentionally linux/amd64: the pinned Temurin archive is x86-64.
FROM ubuntu:22.04@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl python3 hostname procps tar gzip coreutils \
    && rm -rf /var/lib/apt/lists/*

ARG MAVEN_VERSION=3.9.9
ARG MAVEN_SHA512=a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b
RUN curl -fL --retry 3 --max-time 180 \
      "https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz" \
      -o /tmp/maven.tar.gz \
    && printf '%s  /tmp/maven.tar.gz\n' "$MAVEN_SHA512" | sha512sum -c - \
    && mkdir /opt/maven && tar -xzf /tmp/maven.tar.gz --strip-components=1 -C /opt/maven \
    && rm /tmp/maven.tar.gz

WORKDIR /opt/nis2-legolas
COPY scripts/prepare.sh ./scripts/prepare.sh
ENV JAVA_HOME=/opt/nis2-legolas/.local/jdk8 \
    PATH=/opt/nis2-legolas/.local/jdk8/bin:/opt/maven/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 LC_ALL=C.UTF-8

# No host .local directory or Maven cache is copied into the image.
RUN mkdir -p build-evidence \
    && bash scripts/prepare.sh 2>&1 | tee build-evidence/prepare.log
RUN java -version > build-evidence/java.txt 2>&1 \
    && mvn -version > build-evidence/maven.txt \
    && dpkg-query -W > build-evidence/os-packages.txt \
    && (cd .local/legolas && mvn -B -ntp -Dmaven.repo.local=../m2 \
        -pl analyzer,reporter,injector,orchestrator,driver/zookeeper/3.6.2 -am package) \
        2>&1 | tee build-evidence/legolas-build.log
RUN (cd .local/zookeeper && mvn -B -ntp -Dmaven.repo.local=../m2-zookeeper \
        -pl zookeeper-server -am -DskipTests -Dmaven.javadoc.skip=true package) \
        2>&1 | tee build-evidence/zookeeper-build.log
RUN export LEGOLAS_JAVA_OPTS='-Xmx4g -XX:ActiveProcessorCount=4' \
    && (cd .local/legolas && bash scripts/analysis/analyze-zookeeper.sh -i ../zookeeper 3.6.2) \
        2>&1 | tee build-evidence/analysis.log \
    && grep -q 'Legolas analyzer finished' build-evidence/analysis.log \
    && test -s .local/legolas/data/injection_points.csv \
    && test -f .local/zookeeper/zookeeper-server/target/classes/edu/umich/order/legolas/common/agent/LegolasAgent.class

RUN cp .local/legolas/data/abstract_states.csv .local/legolas/data/injection_points.csv build-evidence/ \
    && mkdir -p .local/legolas/workspace .local/legolas/logs /results \
    && chmod 1777 .local/legolas/workspace .local/legolas/logs /results

COPY scripts/run_logged.py ./scripts/run_logged.py
COPY scripts/checkpoint-1/smoke_run.py scripts/checkpoint-1/summarize_smoke.py scripts/checkpoint-1/entrypoint.sh ./scripts/checkpoint-1/

# Arbitrary host UID works: no privileged mode, host PID/network or Docker socket.
# Explicit JVM user name keeps upstream log filenames consistent for numeric UIDs.
ENV EVIDENCE_DIR=/results USER=legolas HOME=/tmp
USER 1000:1000
ENTRYPOINT ["bash", "/opt/nis2-legolas/scripts/checkpoint-1/entrypoint.sh"]
CMD ["control", "--policy", "None"]
