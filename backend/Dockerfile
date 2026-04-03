# ベースイメージ: Python 3.12 slim
FROM python:3.12-slim

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 作業ディレクトリ
WORKDIR /app

# システム依存パッケージのインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python依存パッケージのインストール
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート公開（Railway は $PORT 環境変数でポートを指定）
EXPOSE ${PORT:-8000}

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(f'http://localhost:{__import__(\"os\").environ.get(\"PORT\", \"8000\")}/health')" || exit 1

# アプリケーション起動（Railway の $PORT に対応）
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
