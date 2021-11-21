FROM acidrain/python-poetry:3.9-alpine

ENV PROJECT_ROOT "/app"
ENV PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"
ENV PYTHONOPTIMIZE=1
ENV CACHE_FOLDER=/var/cache/aoc_dashboard

WORKDIR "${PROJECT_ROOT}"
VOLUME /var/cache/aoc_dashboard
EXPOSE 8000

COPY pyproject.toml poetry.lock  "${PROJECT_ROOT}"/

RUN set -eu; \
    poetry config virtualenvs.in-project true; \
    poetry install --no-dev; \
    rm -rf ~/.cache/pypoetry;

COPY aoc_dashboard "${PROJECT_ROOT}"/aoc_dashboard
COPY templates "${PROJECT_ROOT}"/templates

# Compile bytecode for faster startup
RUN python -m compileall *

CMD ["uvicorn", "--host", "0.0.0.0", "aoc_dashboard:app"]
