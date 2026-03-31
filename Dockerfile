FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libsndfile1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 🔥 instala uv (e uvx)
RUN curl -Ls https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

COPY . /app

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -e .
RUN pip install fastapi uvicorn python-multipart jinja2
RUN python -m spacy download en_core_web_sm

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
