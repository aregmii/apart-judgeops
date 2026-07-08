FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
COPY . .
RUN uv sync
ENTRYPOINT ["uv", "run", "judgeops"]
CMD ["--help"]
