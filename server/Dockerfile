# 打刻システム - サーバー用Dockerfile
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# 依存パッケージのインストール
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

# アプリケーションファイルをコピー
COPY server.py .
COPY database.py .
COPY utils.py .
COPY config.py .
COPY overtime.py .
COPY leave_request.py .
COPY api_attendance.py .
COPY api_overtime.py .
COPY api_leave.py .
COPY api_monthly_report.py .
COPY auth.py .
COPY monthly_report.py .
COPY pdf_generator.py .
COPY templates/ templates/

# データディレクトリの作成（マウントポイント）
RUN mkdir -p /app/data

# ポート5000を公開
EXPOSE 5000

# 環境変数
ENV FLASK_APP=server.py
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/attendance.db

# サーバー起動
CMD ["python", "server.py"]

