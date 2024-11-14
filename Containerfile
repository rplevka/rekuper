FROM quay.io/fedora/python-312:latest
MAINTAINER https://github.com/SatelliteQE

ENV REKUPER_DIR="${HOME}/rekuper"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

USER 1001
COPY --chown=1001:0 / ${REKUPER_DIR}

WORKDIR ${REKUPER_DIR}
RUN rm -f settings.yaml scripts/shovel/settings.yaml && \
    git config --global --add safe.directory ${REKUPER_DIR} && \
    uv pip install -r requirements.txt -r requirements-shovel.txt

CMD flask --app rekuper run --host 0.0.0.0
