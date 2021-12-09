set dotenv-load := true

run: _deps
    poetry run uvicorn --reload aoc_dashboard:app

run-webapp: _webapp_deps
    cd webapp; yarn start

build:
    docker buildx build -t aoc-dashboard --build-arg SERVER_URL .

_deps:
    [[ ! -f .just.poetry || poetry.lock -nt .just.poetry ]] && ( poetry install; touch .just.poetry ) || true

_webapp_deps:
    [[ ! -f .just.yarn || webapp/yarn.lock -nt .just.yarn ]] && ( pushd webapp; yarn install; popd; touch .just.yarn ) || true
