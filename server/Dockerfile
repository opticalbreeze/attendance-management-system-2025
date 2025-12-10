# 打刻システム - サーバー用Dockerfile
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# WeasyPrintの依存関係と日本語フォントをインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgobject-2.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    && rm -rf /var/lib/apt/lists/*

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
COPY api_check_status.py .
COPY auth.py .
COPY monthly_report.py .
COPY pdf_generator.py .
COPY logger_config.py .
COPY database_utils.py .
COPY time_utils.py .
COPY validation_utils.py .
COPY api_utils.py .
COPY pdf_utils.py .
COPY admin.py .
COPY work_type_constants.py .
COPY attendance_check_service.py .
COPY import_schedule_csv.py .
COPY templates/ templates/
COPY static/ static/

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

