FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY pyproject.toml uv.lock ./

RUN uv sync \
    --locked \
    --no-dev \
    --no-install-project

COPY . .

# The current settings require database variables during Django startup,
# but collectstatic does not connect to the database.
RUN DB_NAME=build \
    DB_HOST=build \
    DB_USER=build \
    DB_PASSWORD=build \
    python manage.py collectstatic --noinput

RUN groupadd --system django \
    && useradd --system --gid django --no-create-home django

USER django

EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn tomo.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout 60 --access-logfile - --error-logfile -"]