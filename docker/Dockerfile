# Experimental runtime-validation branch only. The production Dockerfile remains
# unchanged on the parent integration branch. Reuse the owner's existing image.
FROM acaicia/minkowski4cpp@sha256:a4bf4c4e91ef5f4e50089f435005ca07f1a0a48deeeb9814ca4b526974de79ba

# The inherited CI has three matrix labels. All three deliberately execute this
# SAME CUDA 13.4 / LibTorch image in CPU_ONLY mode; they are repeated runs, not
# CUDA 12.4/13.2 runtime compatibility claims.
ARG CUDA_VERSION
ARG JOBS=2
ENV CUDA_VISIBLE_DEVICES="" NVIDIA_VISIBLE_DEVICES=void \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OMP_DYNAMIC=FALSE \
    TORCH_CUDA_ARCH_LIST=7.5

WORKDIR /opt/minkowski-runtime/source
COPY . .
RUN python3 -B tests/container_runtime/test_evidence.py && \
    python3 tests/container_runtime/run.py \
      --source /opt/minkowski-runtime/source \
      --build /opt/minkowski-runtime/build \
      --output /opt/minkowski-runtime/evidence \
      --jobs ${JOBS} --expected-tests 9 \
      --image-digest sha256:a4bf4c4e91ef5f4e50089f435005ca07f1a0a48deeeb9814ca4b526974de79ba

WORKDIR /workspace
CMD ["/bin/bash"]
