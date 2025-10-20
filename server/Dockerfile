# 打刻システム - サーバー用Dockerfile
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# 依存パッケージのインストール
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

# アプリケーションファイルをコピー
COPY server.py .
COPY templates/ templates/

# データベースディレクトリの作成（永続化用）
RUN mkdir -p /data

# ポート5000を公開
EXPOSE 5000

# 環境変数
ENV FLASK_APP=server.py
ENV PYTHONUNBUFFERED=1

# サーバー起動
CMD ["python", "server.py"]

