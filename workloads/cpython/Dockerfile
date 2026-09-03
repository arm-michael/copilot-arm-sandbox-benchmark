# syntax=docker/dockerfile:1.12

ARG TARGETPLATFORM
FROM --platform=${TARGETPLATFORM} gcc:14-bookworm@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15 AS prepared

WORKDIR /src
COPY cpython.tgz /tmp/cpython.tgz
RUN tar -xzf /tmp/cpython.tgz --strip-components=1 \
    && rm /tmp/cpython.tgz

FROM prepared AS benchmark
ARG BENCHMARK_ITERATION=0
RUN printf '%s\n' "${BENCHMARK_ITERATION}" > /benchmark-iteration \
    && ./configure --with-ensurepip=no \
    && make -j 4 \
    && readelf -h python | grep -q 'Machine:.*AArch64' \
    && ./python -m test -j 4 test_json test_math test_re test_statistics test_unicode

