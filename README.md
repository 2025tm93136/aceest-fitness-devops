# ACEest Fitness & Gym — CI/CD with Flask, Docker, Jenkins & GitHub Actions

![CI/CD Pipeline](https://github.com/2025tm93136/aceest-fitness-devops/actions/workflows/main.yml/badge.svg)

A Flask REST service for ACEest Fitness & Gym, ported from the provided Tkinter desktop versions (1.0 → 3.2.4), with an automated build, test and containerisation pipeline.

## Features / API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/`, `/health` | Service info / health check |
| GET | `/programs`, `/programs/<code>` | Programs (FL, MG, BG) with workout & diet plans |
| POST | `/bmi` | BMI from `{weight, height}` |
| GET/POST | `/clients` | List / create clients (calories auto-calculated: weight × program factor) |
| GET/DELETE | `/clients/<name>` | Get / delete a client |
| GET | `/clients/<name>/membership` | Membership status |
| GET/POST | `/clients/<name>/progress` | Weekly adherence (0–100) and average |
| GET/POST | `/clients/<name>/workouts` | Workout log (Strength, Hypertrophy, Cardio, Mobility) |

## Project structure

```
app.py                     Flask application
requirements.txt           Runtime dependencies
requirements-dev.txt       Test/lint dependencies
tests/test_app.py          Pytest suite
Dockerfile                 Multi-stage image (test + runtime)
Jenkinsfile                Jenkins BUILD pipeline
.github/workflows/main.yml GitHub Actions CI/CD
```

## Local setup and execution

```bash
git clone https://github.com/2025tm93136/aceest-fitness-devops.git
cd aceest-fitness-devops
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python app.py            # http://localhost:5000
```

Example:

```bash
curl -X POST localhost:5000/clients -H "Content-Type: application/json" \
     -d '{"name":"Arun","age":28,"weight":80,"program":"FL"}'
```

### Run with Docker

```bash
docker build --target runtime -t aceest-fitness .
docker run -p 5000:5000 aceest-fitness
```

## Running tests manually

```bash
pytest -v                 # locally
flake8 .                  # lint
docker build --target test -t aceest-fitness:test . && docker run --rm aceest-fitness:test   # inside container
```

## CI/CD overview

**Dockerfile** — multi-stage on `python:3.12-slim`: a `test` stage (adds pytest/flake8 + tests) and a lean `runtime` stage that runs gunicorn as a non-root user with a health check. Dev tools and tests never ship in the production image.

**GitHub Actions** (`.github/workflows/main.yml`) runs on every `push` and `pull_request`:
1. **Build & Lint** — install deps, `py_compile` syntax check, `flake8`.
2. **Docker Build & Test** — build the `test` image and run Pytest inside the container, then build the `runtime` image and smoke-test `/health`.

**Jenkins** (`Jenkinsfile`) is the secondary build/quality gate. A Pipeline job ("Pipeline script from SCM", pointing at this repo) pulls the latest code from GitHub and runs: Checkout → Build & Lint → Unit Tests (JUnit report) → Docker Build, then cleans the workspace for a clean build each time. It can be triggered manually, by SCM polling, or by a GitHub webhook.

```
git push ──► GitHub ──► GitHub Actions: lint → docker build → pytest in container
                   └──► Jenkins: checkout → lint → pytest → docker build
```

## Branching strategy

`main` holds stable code; work is done on `feature/*`, `test/*` and `infra/*` branches and merged into `main` with descriptive commits.
