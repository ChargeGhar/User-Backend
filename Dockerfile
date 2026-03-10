FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /application

# Copy project files (excluding .venv)
COPY pyproject.toml uv.lock ./
COPY api/ ./api/
COPY manage.py ./
COPY Makefile ./

# Install dependencies into /opt/venv (outside the project dir so bind mount
# volumes don't interfere with the pre-built venv on container startup)
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv sync --frozen

# Set environment variable to use uv's virtual environment
ENV PATH="/opt/venv/bin:$PATH"
