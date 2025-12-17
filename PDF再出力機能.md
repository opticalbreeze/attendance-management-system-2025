# PDF再出力機能

## 概要

一度PDF出力した休暇願や時間外申告を、既存の申請データから再度PDF出力する機能です。

## 実装内容

既存の関数を最大限活用してシンプルに実装しました。

### 使用している既存関数

1. **`generate_overtime_html`** (`pdf_generator.py`)
   - 時間外申告のHTMLコンテンツを生成

2. **`generate_leave_html`** (`pdf_generator.py`)
   - 休暇願のHTMLコンテンツを生成

3. **`save_pdf_from_html`** (`pdf_utils.py`)
   - HTMLコンテンツからPDFを生成して保存

## APIエンドポイント

### 時間外申告PDF再出力

```
POST /api/overtime/<overtime_id>/reprint_pdf
```

**パラメータ**:
- `overtime_id` (URLパラメータ): 時間外申告ID

**レスポンス**:
```json
{
  "status": "success",
  "message": "PDFを保存しました: YYYYMMDD_従業員名_HHMMSS.pdf",
  "filename": "YYYYMMDD_従業員名_HHMMSS.pdf",
  "path": "/path/to/pdf/file.pdf"
}
```

**エラー時**:
```json
{
  "status": "error",
  "message": "エラーメッセージ"
}
```

### 休暇願PDF再出力

```
POST /api/leave/<leave_id>/reprint_pdf
```

**パラメータ**:
- `leave_id` (URLパラメータ): 休暇願ID

**レスポンス**:
```json
{
  "status": "success",
  "message": "PDFを保存しました: YYYYMMDD_従業員名_HHMMSS.pdf",
  "filename": "YYYYMMDD_従業員名_HHMMSS.pdf",
  "path": "/path/to/pdf/file.pdf"
}
```

**エラー時**:
```json
{
  "status": "error",
  "message": "エラーメッセージ"
}
```

## 実装の流れ

### 時間外申告PDF再出力

1. データベースから時間外申告データを取得（IDで検索）
2. 取得したデータから必要な情報を抽出
3. `generate_overtime_html`でHTMLコンテンツを生成
4. `save_pdf_from_html`でPDFを保存

### 休暇願PDF再出力

1. データベースから休暇願データを取得（IDで検索）
2. 取得したデータから必要な情報を抽出
3. `generate_leave_html`でHTMLコンテンツを生成
4. `save_pdf_from_html`でPDFを保存

## 使用例

### JavaScript (fetch API)

```javascript
// 時間外申告PDF再出力
async function reprintOvertimePDF(overtimeId) {
    try {
        const response = await fetch(`/api/overtime/${overtimeId}/reprint_pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert(`PDFを保存しました: ${result.filename}`);
        } else {
            alert(`エラー: ${result.message}`);
        }
    } catch (error) {
        console.error('PDF再出力エラー:', error);
        alert('PDF再出力中にエラーが発生しました');
    }
}

// 休暇願PDF再出力
async function reprintLeavePDF(leaveId) {
    try {
        const response = await fetch(`/api/leave/${leaveId}/reprint_pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert(`PDFを保存しました: ${result.filename}`);
        } else {
            alert(`エラー: ${result.message}`);
        }
    } catch (error) {
        console.error('PDF再出力エラー:', error);
        alert('PDF再出力中にエラーが発生しました');
    }
}
```

### Python (requests)

```python
import requests

# 時間外申告PDF再出力
def reprint_overtime_pdf(overtime_id):
    url = f'http://localhost:5000/api/overtime/{overtime_id}/reprint_pdf'
    response = requests.post(url)
    result = response.json()
    
    if result['status'] == 'success':
        print(f"PDFを保存しました: {result['filename']}")
        print(f"パス: {result['path']}")
    else:
        print(f"エラー: {result['message']}")

# 休暇願PDF再出力
def reprint_leave_pdf(leave_id):
    url = f'http://localhost:5000/api/leave/{leave_id}/reprint_pdf'
    response = requests.post(url)
    result = response.json()
    
    if result['status'] == 'success':
        print(f"PDFを保存しました: {result['filename']}")
        print(f"パス: {result['path']}")
    else:
        print(f"エラー: {result['message']}")
```

## 保存先

PDFファイルは既存の保存ロジックと同じ場所に保存されます：

- 保存先: `{PDF_SAVE_DIR}/{従業員名}_{月度}/`
- ファイル名: `{YYYYMMDD}_{従業員名}_{HHMMSS}.pdf`

例: `PDF/田中　宏和_202512/20251215_田中　宏和_143022.pdf`

## エラーハンドリング

- 申請IDが見つからない場合: 404エラーを返す
- データベースエラー: 500エラーを返す
- PDF生成エラー: 500エラーを返す（エラーメッセージを含む）

## 注意事項

1. **認証**: これらのエンドポイントは認証が必要な場合があります（`@login_required`デコレータの有無を確認）
2. **権限**: 管理者権限が必要な場合があります
3. **PDF保存先**: 既存のPDF保存先と同じ場所に保存されます（上書きされず、新しいファイルとして保存）

## 実装ファイル

- `work_attend_server/server/api_overtime.py`: 時間外申告PDF再出力エンドポイント
- `work_attend_server/server/api_leave.py`: 休暇願PDF再出力エンドポイント

## テスト方法

1. 既存の時間外申告または休暇願のIDを取得
2. 上記のAPIエンドポイントにPOSTリクエストを送信
3. PDFファイルが正しく生成されることを確認

