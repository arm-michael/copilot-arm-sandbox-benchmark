# syntax=docker/dockerfile:1.12@sha256:93bfd3b68c109427185cd78b4779fc82b484b0b7618e36d0f104d4d801e66d25

ARG TARGETPLATFORM
FROM --platform=${TARGETPLATFORM} gcc:14-bookworm@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15 AS prepared

WORKDIR /src
COPY cpython.tgz /tmp/cpython.tgz
RUN tar -xzf /tmp/cpython.tgz --strip-components=1 \
    && rm /tmp/cpython.tgz

FROM prepared AS benchmark
ARG BENCHMARK_ITERATION=0
RUN mkdir -p /evidence \
    && printf '%s\n' "${BENCHMARK_ITERATION}" > /benchmark-iteration \
    && ./configure --with-ensurepip=no \
    && make -j 4 \
    && readelf -h python > /evidence/elf-header.txt \
    && grep -q 'Machine:.*AArch64' /evidence/elf-header.txt \
    && sha256sum python > /evidence/artifact-sha256.txt \
    && { test_status=0; ./python -m test -j 4 test_json test_math test_re test_statistics test_str > /evidence/tests.txt 2>&1 || test_status=$?; cat /evidence/tests.txt; test "${test_status}" -eq 0; } \
    && printf '{"suite":"cpython-regression-subset","status":"passed"}\n' > /evidence/test-result.json

FROM scratch AS evidence
COPY --from=benchmark /evidence/ /
