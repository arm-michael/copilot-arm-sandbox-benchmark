# syntax=docker/dockerfile:1.12@sha256:93bfd3b68c109427185cd78b4779fc82b484b0b7618e36d0f104d4d801e66d25

ARG TARGETPLATFORM
FROM --platform=${TARGETPLATFORM} python:3.11-bookworm@sha256:35d3a4a3d5e42e02ab916d44513a050689f12c0533d45598d229672503fe77ca AS prepared

WORKDIR /src
COPY brotli.tar.gz /tmp/brotli.tar.gz
RUN tar -xzf /tmp/brotli.tar.gz --strip-components=1 \
    && rm /tmp/brotli.tar.gz

FROM prepared AS benchmark
ARG BENCHMARK_ITERATION=0
RUN mkdir -p /evidence \
    && printf '%s\n' "${BENCHMARK_ITERATION}" > /benchmark-iteration \
    && python setup.py build_ext --inplace -j 4 \
    && readelf -h python/_brotli*.so > /evidence/elf-header.txt \
    && grep -q 'Machine:.*AArch64' /evidence/elf-header.txt \
    && sha256sum python/_brotli*.so > /evidence/artifact-sha256.txt \
    && { test_status=0; PYTHONPATH=/src/python python -m unittest discover -s python -p '*_test.py' > /evidence/tests.txt 2>&1 || test_status=$?; cat /evidence/tests.txt; test "${test_status}" -eq 0; } \
    && printf '{"suite":"brotli-unittest","status":"passed"}\n' > /evidence/test-result.json \
    && PYTHONPATH=/src/python python -c "import brotli,hashlib; p=(b'native-arm64-copilot-sandbox\\n'*(64*1024*1024//29+1))[:64*1024*1024]; c=brotli.compress(p,quality=11); assert brotli.decompress(c)==p; print('brotli-roundtrip',len(p),len(c),hashlib.sha256(p).hexdigest())" > /evidence/compression.txt \
    && cat /evidence/compression.txt

FROM scratch AS evidence
COPY --from=benchmark /evidence/ /
