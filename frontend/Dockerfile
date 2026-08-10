FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml ./
COPY analytics ./analytics
COPY backend ./backend
COPY scripts ./scripts
COPY frontend ./frontend
RUN pip install --upgrade pip && pip install .

EXPOSE 8501
CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
