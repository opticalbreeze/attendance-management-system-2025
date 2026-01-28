#!/bin/bash
# 開発環境チェックスクリプト

echo "🚨 環境分離チェック"
echo "運用環境（5000）の確認..."
curl -s http://localhost:5000/api/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 運用環境（5000）稼働中"
else
    echo "❌ 運用環境（5000）停止中"
fi

echo "開発環境（5001）の確認..."
curl -s http://localhost:5001/api/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 開発環境（5001）稼働中"
else
    echo "❌ 開発環境（5001）停止中"
    echo "開発環境を起動してください："
    echo "docker-compose -f docker-compose.dev.yml up -d"
fi

echo "現在のPythonプロセス："
tasklist /FI "IMAGENAME eq python.exe"