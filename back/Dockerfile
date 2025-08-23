FROM python:3.13.5-slim

WORKDIR /app

COPY uv.lock pyproject.toml ./

RUN pip install --no-cache uv==0.7.21

ENV UV_PROJECT_ENVIRONMENT=/usr/local

RUN uv sync --locked

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]