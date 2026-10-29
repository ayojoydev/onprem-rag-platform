FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -c requirements.lock . && useradd --uid 10001 --create-home simulator \
    && mkdir -p /app/data && chown -R simulator:simulator /app/data
USER simulator
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "-m", "business_api_simulator", "--host", "0.0.0.0", "--port", "8080"]
