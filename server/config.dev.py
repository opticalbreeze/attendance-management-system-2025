# 開発環境用設定
# 本番環境と開発環境を区別するための環境別設定

# 開発環境識別
DEVELOPMENT_MODE=true

# サーバー設定
DEV_SERVER_PORT=5001
DEV_SERVER_HOST=localhost
DEV_DEBUG=True

# データベース設定（本番と共有）
SHARED_DATABASE_PATH=../../data/attendance.db
DEV_LOG_PATH=../../dev_logs

# お知らせ機能開発用設定
NOTIFICATION_DEBUG=True
NOTIFICATION_LOG_LEVEL=DEBUG

# カードリーダーテスト用設定
MOCK_CARD_ENABLED=True
TEST_CARD_IDS=["0123456789ABCDEF", "FEDCBA9876543210"]

# 開発用セキュリティ設定（本番では使用禁止）
DEV_SECRET_KEY=dev-secret-key
DEV_BYPASS_AUTH=False  # 認証バイパス（危険、本番では必ずFalse）