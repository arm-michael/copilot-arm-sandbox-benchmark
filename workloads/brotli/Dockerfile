# syntax=docker/dockerfile:1.12

ARG TARGETPLATFORM
FROM --platform=${TARGETPLATFORM} python:3.11-bookworm@sha256:35d3a4a3d5e42e02ab916d44513a050689f12c0533d45598d229672503fe77ca AS prepared

WORKDIR /src
COPY brotli.tar.gz /tmp/brotli.tar.gz
RUN tar -xzf /tmp/brotli.tar.gz --strip-components=1 \
    && rm /tmp/brotli.tar.gz

FROM prepared AS benchmark
ARG BENCHMARK_ITERATION=0
RUN printf '%s\n' "${BENCHMARK_ITERATION}" > /benchmark-iteration \
    && python setup.py build_ext --inplace -j 4 \
    && readelf -h _brotli*.so | grep -q 'Machine:.*AArch64' \
    && PYTHONPATH=/src python -m unittest discover -s python -p '*_test.py' \
    && PYTHONPATH=/src python -c "import brotli,hashlib; p=(b'native-arm64-copilot-sandbox\\n'*(64*1024*1024//29+1))[:64*1024*1024]; c=brotli.compress(p,quality=11); assert brotli.decompress(c)==p; print('brotli-roundtrip',len(p),len(c),hashlib.sha256(p).hexdigest())"

