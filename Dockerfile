ARG USER=app

FROM python:3.13-slim as base-image

ARG USER

ENV PYTHONUNBUFFERED=1
ENV APP_WORKDIR=/home/$USER
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

RUN groupadd --system $USER && \
    useradd --system --create-home --gid $USER $USER

WORKDIR $APP_WORKDIR

FROM base-image as builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
        openssh-client \
        python3-dev \
        libffi-dev \
        && \
    pip install uv \
    && \
    rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml ./
RUN uv sync --no-dev

FROM base-image

ENV PATH=$APP_WORKDIR/.venv/bin:$PATH

WORKDIR $APP_WORKDIR

COPY --chown=$USER:$USER entrypoint.sh /entrypoint.sh
COPY --from=builder --chown=$USER:$USER $APP_WORKDIR/.venv .venv
COPY --chown=$USER:$USER . .

USER $USER
ENTRYPOINT ["/entrypoint.sh"]
CMD [ "uvicorn", "gas.app:app" ]
