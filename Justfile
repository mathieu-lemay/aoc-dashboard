set dotenv-load := true

run: _deps
    poetry run uvicorn --reload aoc_dashboard:app

_deps:
    [[ ! -f .just.poetry || poetry.lock -nt .just.poetry ]] && ( poetry install; touch .just.poetry ) || true
