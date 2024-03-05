# syntax=docker/dockerfile:1.4
ARG PYTHON_IMAGE=pypy:3.9-7.3.15-slim-bookworm
ARG PYTHON=pypy3
ARG PATHON_PATH=/opt/pypy

FROM ${PYTHON_IMAGE} as base

WORKDIR /opt/koe

RUN rm -f /etc/apt/apt.conf.d/docker-clean

################################################################################

FROM base as builder
ARG BUILDPLATFORM

RUN \
    --mount=type=cache,id=$BUILDPLATFORM:/var/cache,target=/var/cache,sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
		build-essential \
		make \
	;

COPY requirements.txt ./

RUN \
    --mount=type=cache,id=$BUILDPLATFORM:.cache/pip,target=.cache/pip,sharing=locked \
    pip install --cache-dir .cache/pip -r requirements.txt

################################################################################

FROM base
ARG PYTHON
ARG PATHON_PATH

COPY --link . .
COPY --link --from=builder ${PATHON_PATH} ${PATHON_PATH}

VOLUME /opt/koe/data

ENV PYTHON "${PYTHON}"

ENTRYPOINT ${PYTHON} -m koe
