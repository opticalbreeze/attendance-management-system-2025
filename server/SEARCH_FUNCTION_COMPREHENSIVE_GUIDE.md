# 🔍 検索機能 包括的ガイド - 問題分析・解決策・再発防止策

## 📋 概要

このドキュメントは、検索機能で繰り返し発生している問題を統合的に分析し、根本原因、解決策、再発防止策をまとめた包括的なガイドです。

**作成日**: 2026年1月29日  
**統合元ドキュメント**:
- `AI_CODING_PROBLEMS_ANALYSIS.md`
- `SEARCH_PAGE_TROUBLESHOOTING.md`
- `GLOBAL_FUNCTIONS_ANALYSIS.md`
- `CODE_ANALYSIS_REPORT.md`
- `DIAGNOSE_SEARCH_ERROR.md`
- `QUICK_FIX_SEARCH.md`
- `SEARCH_FIX_VERIFICATION.md`
- `FIX_ATTENDANCE_COMMON_LOADING.md`

---

## 🚨 問題の概要

### 核心的な問題

**「searchを改善すると必ず一度は検索ができなくなる」という問題が繰り返し発生している。**

この問題は、以下の複数の要因が複合的に作用しています：

1. **グローバル関数の競合**
2. **スクリプトの読み込み順序への依存**
3. **APIエンドポイントの過度な依存**
4. **環境間の差異（templates vs templates_dev）**
5. **関数の重複定義**

### 問題の歴史

- **2026年1月27日**: 検索機能の問題が複数回発生
- **2026年1月28日**: `a1c9e52`コミットでフォーム送信リスナーの設定位置が変更され、検索が動かなくなる
- **2026年1月29日**: 問題が再発し、根本原因の分析を実施
- **継続的な問題**: 「一週間近く同じような問題でいたちごっこしている」

---

## 🔍 根本原因の詳細分析

### 1. グローバル関数の競合（最重要）

#### 1.1 `performSearch`関数の競合

**定義箇所1**: `static/js/attendance-check.js` 100行目
```javascript
async function performSearch(event) {
    event.preventDefault();
    // ...
}
```

**定義箇所2**: `templates/search.html` 内（`AttendanceSystem.Search.performSearch`として）
```javascript
AttendanceSystem.Search.performSearch = async function(options) {
    // ...
}
```

**問題点**:
- `attendance-check.js`の`performSearch`はグローバル関数として定義されている
- `search.html`では`AttendanceSystem.Search.performSearch`として名前空間内に定義されている
- イベントリスナーがどちらを参照するかが不明確
- スクリプトの読み込み順序によって動作が変わる

**影響**:
- `attendance-check.js`が先に読み込まれると、グローバルの`performSearch`が定義される
- `search.html`のスクリプトが後で読み込まれると、`AttendanceSystem.Search.performSearch`が定義される
- イベントリスナーがどちらを参照するかによって動作が変わる

#### 1.2 `displayResults`関数の競合

**定義箇所1**: `static/js/attendance-check.js` 154行目
```javascript
function displayResults(results, searchParams) {
    // 基本版（時間外判定なし）
}
```

**定義箇所2**: `templates/search.html` 461行目
```javascript
async function displayResults(results, searchParams) {
    // 拡張版（時間外判定あり）
    AttendanceSystem.Search.displayResults(results, searchParams);
}
```

**定義箇所3**: `static/js/attendance-common.js` 471行目
```javascript
AttendanceSystem.Search.displayResults = function(results, searchParams) {
    // 実装版
}
```

**問題点**:
- 3箇所で定義されている
- `search.html`の`displayResults`が`AttendanceSystem.Search.displayResults`を呼び出している
- `attendance-check.js`の`displayResults`はグローバル関数として定義されている
- 実際に使用されるのは`search.html`の`displayResults`（最後に読み込まれるため）

**影響**:
- `attendance-check.js`の`displayResults`は実質的に無効化されている
- `search.html`の`displayResults`が使用されるが、内部で`AttendanceSystem.Search.displayResults`を呼び出している
- 関数の呼び出しチェーンが複雑になり、デバッグが困難

#### 1.3 `searchResults`グローバル変数の競合

**定義箇所1**: `static/js/attendance-check.js` 2行目
```javascript
let searchResults = [];
```

**定義箇所2**: `templates/search.html` 302行目
```javascript
AttendanceSystem.Search.searchResults = [];
```

**問題点**:
- `attendance-check.js`ではグローバル変数として定義
- `search.html`では名前空間内に定義
- 両方が存在し、どちらが使用されるかが不明確

**影響**:
- `attendance-check.js`の`displayResults`はグローバルの`searchResults`を使用
- `search.html`の`displayResults`は`AttendanceSystem.Search.searchResults`を使用
- データの不整合が発生する可能性

### 2. スクリプトの読み込み順序の問題

**読み込み順序**（`templates/search.html` 266-269行目）:
```html
<script src="{{ url_for('static', filename='js/attendance-common.js') }}"></script>
<script src="{{ url_for('static', filename='js/attendance-check.js') }}"></script>
<script src="{{ url_for('static', filename='js/api-service.js') }}"></script>
<script src="{{ url_for('static', filename='js/employee-list.js') }}"></script>
<script>
    // search.html内のスクリプト
</script>
```

**問題点**:
1. `attendance-common.js`が最初に読み込まれ、`AttendanceSystem`名前空間を初期化
2. `attendance-check.js`が次に読み込まれ、グローバル関数を定義
3. `search.html`内のスクリプトが最後に読み込まれ、関数を上書き

**影響**:
- 読み込み順序が変わると動作が変わる
- 関数の上書きが予期しない動作を引き起こす
- デバッグが困難

### 3. DOMContentLoadedイベントリスナーの問題

**問題の発生**:
- コミット `a1c9e52`（2026-01-28）でフォーム送信リスナーの設定位置が変更された
- フォーム送信リスナーが2つ目の`DOMContentLoaded`内に移動された
- 2つの`DOMContentLoaded`イベントリスナーが存在し、実行順序が保証されない

**変更前（動作していた状態）**:
```javascript
// フォーム送信
document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    await performSearch();
});
```

**変更後（動作しなくなった状態）**:
```javascript
// DOMContentLoaded後に設定
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await performSearch();
        });
    }
});
```

**問題点**:
- 複数の`DOMContentLoaded`イベントリスナーが存在
- 実行順序が保証されず、フォーム送信リスナーが設定されない可能性がある

### 4. APIエンドポイントの過度な依存

**問題点**:
- `/api/search`エンドポイントが2つの機能を同時に処理している：
  1. **検索機能**: スケジュールデータの検索
  2. **エラー・警告取得機能**: 各日付に対して`check_attendance_vs_schedule`を呼び出してアラートを取得

**コード箇所**: `api_attendance.py` 115-141行目
```python
# 各日付に対してアラート情報と実際の打刻時刻を取得
for item in results:
    try:
        check_result = check_attendance_vs_schedule(employee_id, item['work_date'])
        # ...
    except Exception as e:
        item['alerts'] = []
```

**影響**:
- エラー・警告取得ロジックを変更すると、検索API全体が影響を受ける
- 検索機能のパフォーマンス改善を試みると、エラー・警告取得のタイミングや処理が影響を受ける
- 一方の機能を修正すると、他方の機能が壊れるリスクが常に存在

### 5. 環境間の差異（templates vs templates_dev）

**問題点**:
- `templates/search.html`（5000用）と`templates_dev/search.html`（5001用）が異なる内容を持っている
- ハッシュ値が異なる（`E395DDA64C52B9C2523E121E962072D2` vs `F5D960B38F6AF2F5985906CFF793B492`）

**影響**:
- 5001で修正した内容が5000に反映されない
- 5000で修正した内容が5001に反映されない
- 環境間で動作が異なる
- 修正を一方の環境に適用すると、他方の環境で動かなくなる

### 6. 関数の重複定義（同一ファイル内）

**問題点**: `templates/search.html`内で`timeToMinutes`関数が2回定義されている

**定義箇所1**: 1101行目（`compareTimes`関数内のローカル関数）
```javascript
function compareTimes(time1, time2) {
    function timeToMinutes(time) {
        // 戻り値: 0 または 分
    }
}
```

**定義箇所2**: 1297行目（グローバル関数）
```javascript
function timeToMinutes(time) {
    // 戻り値: null または 分
}
```

**影響**:
- 戻り値の型が異なる（`0` vs `null`）
- どちらが使用されるかが不明確
- 予期しない動作を引き起こす可能性

### 7. attendance-common.jsの読み込み問題

**問題**: `AttendanceSystem.Search.performSearch is not a function` エラーが発生

**原因**:
- `attendance-common.js`が読み込まれる前に`AttendanceSystem.Search.performSearch`が呼ばれている可能性
- ブラウザキャッシュの問題
- スクリプトの読み込み順序の問題

---

## 🔄 繰り返し発生するパターン

### パターン1: 関数の上書きによる動作不良

1. `attendance-check.js`の`performSearch`を修正
2. `search.html`の`AttendanceSystem.Search.performSearch`が上書き
3. イベントリスナーがどちらを参照するかが不明確になり、検索が動かなくなる

### パターン2: APIエンドポイントの変更による影響

1. `/api/search`エンドポイントのエラー・警告取得ロジックを変更
2. 検索機能全体が影響を受ける
3. 検索が動かなくなる

### パターン3: 環境間の同期不足

1. 5001（開発環境）で修正を実施
2. `templates_dev/search.html`のみが更新される
3. `templates/search.html`（5000用）が更新されない
4. 5000で動作確認すると、修正が反映されていない
5. 5000で直接修正すると、5001との差異が生じる

### パターン4: グローバル変数の不整合

1. `searchResults`を`attendance-check.js`で使用
2. `AttendanceSystem.Search.searchResults`を`search.html`で使用
3. データの不整合が発生
4. 検索結果が正しく表示されない

### パターン5: DOMContentLoadedの扱いミス

1. フォーム送信リスナーを`DOMContentLoaded`内に移動
2. 複数の`DOMContentLoaded`イベントリスナーが存在
3. 実行順序が保証されず、フォーム送信リスナーが設定されない

---

## 💡 解決策の提案

### 解決策1: グローバル関数の名前空間化（最優先）

**方針**: すべての関数を`AttendanceSystem`名前空間内に移動

**実装**:
1. `attendance-check.js`のグローバル関数を`AttendanceSystem.Check`名前空間に移動
2. `search.html`の関数を`AttendanceSystem.Search`名前空間に統一
3. グローバル変数を`AttendanceSystem.Data`に移動

**メリット**:
- 関数の競合が解消される
- 名前空間が明確になり、デバッグが容易になる
- コードの可読性が向上する

**デメリット**:
- 既存のコードの変更範囲が大きい
- 他のページで`attendance-check.js`の関数を使用している場合は影響がある

### 解決策2: APIエンドポイントの分離

**方針**: 検索機能とエラー・警告取得機能を別々のAPIエンドポイントに分離

**実装**:
1. `/api/search`: スケジュールデータの検索のみ（エラー・警告取得なし）
2. `/api/search/alerts`: 特定の日付範囲のエラー・警告を一括取得

**メリット**:
- 各機能が独立して動作するため、一方の変更が他方に影響しない
- エラー・警告取得のパフォーマンスを最適化しやすい
- キャッシュ戦略を個別に設定できる

**デメリット**:
- フロントエンドで2回のAPI呼び出しが必要になる
- 既存のコードの変更範囲が大きい

### 解決策3: テンプレートファイルの統一

**方針**: `templates/search.html`と`templates_dev/search.html`を統一

**実装**:
1. デプロイスクリプトで`templates_dev/`の変更を`templates/`に自動コピー
2. Gitフックで変更を検知して自動同期
3. Docker Composeでシンボリックリンクを使用

**メリット**:
- 環境間の差異が解消される
- 手動での同期作業が不要になる

**デメリット**:
- 5000と5001で異なる動作を意図している場合は適用できない

### 解決策4: 関数の重複定義の解消

**方針**: 重複している関数を1つに統一

**実装**:
1. `timeToMinutes`関数を1つに統一（`attendance-common.js`に移動）
2. `displayResults`関数を`AttendanceSystem.Search.displayResults`に統一
3. `fetchOvertimeDataForMonth`と`fetchLeaveDataForMonth`を`AttendanceSystem.Search`名前空間に統一

**メリット**:
- 関数の重複が解消される
- コードの保守性が向上する

**デメリット**:
- 既存のコードの変更が必要

### 解決策5: DOMContentLoadedの統一

**方針**: 複数の`DOMContentLoaded`イベントリスナーを1つに統合

**実装**:
1. すべての初期化処理を1つの`DOMContentLoaded`イベントリスナー内に統合
2. フォーム送信リスナーは`DOMContentLoaded`の外で直接設定（動作していた状態に戻す）

**メリット**:
- 実行順序が保証される
- フォーム送信リスナーが確実に設定される

**デメリット**:
- 既存のコードの変更が必要

---

## 🛠️ トラブルシューティングガイド

### 問題1: 検索ボタンをクリックしても検索が実行されない

**症状**:
- 検索ボタンをクリックしても何も起こらない
- ブラウザのコンソールにエラーが表示されない

**診断手順**:

1. **ブラウザコンソールで確認**:
```javascript
// Step 1: AttendanceSystemが定義されているか
console.log('1. AttendanceSystem:', typeof AttendanceSystem);

// Step 2: AttendanceSystem.Searchが定義されているか
console.log('2. AttendanceSystem.Search:', typeof AttendanceSystem?.Search);

// Step 3: performSearch関数が定義されているか
console.log('3. performSearch:', typeof AttendanceSystem?.Search?.performSearch);

// Step 4: attendance-common.jsが読み込まれているか
console.log('4. attendance-common.js loaded:', document.querySelector('script[src*="attendance-common.js"]') !== null);
```

2. **フォーム送信リスナーが設定されているか確認**:
```javascript
// フォーム要素を取得
const form = document.getElementById('search-form');
console.log('Form element:', form);

// イベントリスナーが設定されているか確認
const listeners = getEventListeners(form);
console.log('Event listeners:', listeners);
```

3. **ネットワークタブで確認**:
- `attendance-common.js` が200 OKで読み込まれているか
- `attendance-common.js` のファイルサイズが0バイトでないか
- `attendance-common.js` に構文エラーがないか（Consoleタブで確認）

**解決策**:

1. **ブラウザキャッシュをクリア**:
   - `Ctrl+Shift+R` (強制リロード)
   - または `Ctrl+F5`

2. **フォーム送信リスナーを手動で設定**（一時的な回避策）:
```javascript
// フォーム要素を取得
const form = document.getElementById('search-form');
if (form) {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (typeof AttendanceSystem?.Search?.performSearch === 'function') {
            await AttendanceSystem.Search.performSearch();
        } else {
            console.error('AttendanceSystem.Search.performSearch is not a function');
        }
    });
}
```

3. **DOMContentLoadedの外で直接設定**:
   - `search.html`の340行目付近で、フォーム送信リスナーを`DOMContentLoaded`の外で直接設定する

### 問題2: `AttendanceSystem.Search.performSearch is not a function` エラー

**症状**:
- ブラウザのコンソールに `AttendanceSystem.Search.performSearch is not a function` エラーが表示される

**診断手順**:

1. **ブラウザコンソールで確認**:
```javascript
// AttendanceSystemが定義されているか
typeof AttendanceSystem

// AttendanceSystem.Searchが定義されているか
typeof AttendanceSystem.Search

// performSearch関数が定義されているか
typeof AttendanceSystem.Search.performSearch
```

2. **ファイルの内容を確認**:
```powershell
# attendance-common.jsの最後の10行を確認
Get-Content "C:\Users\take_me_hospital\attendance\work_attend_server\server\static\js\attendance-common.js" | Select-Object -Last 10
```

3. **スクリプトの読み込み順序を確認**:
   - `templates/search.html`で`attendance-common.js`が`attendance-check.js`より前に読み込まれているか確認

**解決策**:

1. **ブラウザキャッシュをクリア**:
   - `Ctrl+Shift+R` (強制リロード)

2. **attendance-common.jsの構文エラーを確認**:
   - ブラウザで`attendance-common.js`を直接開いて、構文エラーがないか確認

3. **スクリプトの読み込み順序を確認**:
   - `attendance-common.js`が最初に読み込まれるようにする

### 問題3: 検索結果が表示されない

**症状**:
- 検索は実行されるが、結果が表示されない

**診断手順**:

1. **APIレスポンスを確認**:
   - ブラウザのネットワークタブで`/api/search`のレスポンスを確認
   - データが正しく返されているか確認

2. **displayResults関数が呼ばれているか確認**:
```javascript
// displayResults関数にブレークポイントを設定
// または、console.logを追加して呼び出しを確認
```

3. **searchResults変数の状態を確認**:
```javascript
// グローバルのsearchResults
console.log('Global searchResults:', typeof searchResults !== 'undefined' ? searchResults : 'undefined');

// AttendanceSystem.Search.searchResults
console.log('AttendanceSystem.Search.searchResults:', AttendanceSystem?.Search?.searchResults);
```

**解決策**:

1. **displayResults関数の呼び出しを確認**:
   - `performSearch`関数内で`displayResults`が正しく呼ばれているか確認

2. **searchResults変数の統一**:
   - `AttendanceSystem.Search.searchResults`を使用するように統一

### 問題4: 5000と5001で動作が異なる

**症状**:
- 5000（本番環境）では動作するが、5001（開発環境）では動作しない、またはその逆

**診断手順**:

1. **テンプレートファイルの差異を確認**:
```powershell
# ファイルのハッシュ値を確認
Get-FileHash "C:\Users\take_me_hospital\attendance\work_attend_server\server\templates\search.html"
Get-FileHash "C:\Users\take_me_hospital\attendance\work_attend_server\server\templates_dev\search.html"
```

2. **Docker Compose設定の差異を確認**:
   - `docker-compose.yml`（5000用）と`docker-compose.dev.yml`（5001用）の`volumes`セクションを比較

3. **静的ファイルの差異を確認**:
   - `static/`と`static_dev/`のファイルを比較

**解決策**:

1. **テンプレートファイルを同期**:
   - `templates_dev/search.html`の変更を`templates/search.html`にコピー

2. **Docker Compose設定を統一**:
   - 可能な限り、5000と5001で同じ設定を使用

---

## 📊 影響範囲のマッピング

### グローバル関数の使用状況

| 関数名 | 定義箇所 | 使用箇所 | 問題 |
|--------|----------|----------|------|
| `performSearch` | `attendance-check.js` (グローバル)<br>`search.html` (`AttendanceSystem.Search`) | `search.html` (イベントリスナー) | 競合 |
| `displayResults` | `attendance-check.js` (グローバル)<br>`search.html` (グローバル)<br>`attendance-common.js` (`AttendanceSystem.Search`) | `performSearch`内 | 競合・上書き |
| `searchResults` | `attendance-check.js` (グローバル)<br>`search.html` (`AttendanceSystem.Search`) | `displayResults`内<br>`exportCSV`内 | 競合 |
| `timeToMinutes` | `search.html` (2箇所) | `compareTimes`内<br>`autoCheckMissingPunchWithOvertime`内 | 重複 |

### スクリプトの依存関係

```
attendance-common.js
  └─ AttendanceSystem名前空間の初期化
  └─ AttendanceSystem.Search.displayResults定義
  └─ AttendanceSystem.Search.performSearch定義

attendance-check.js
  └─ グローバル関数の定義（performSearch, displayResults）
  └─ グローバル変数の定義（searchResults, allEmployees）

search.html内のスクリプト
  └─ AttendanceSystem.Search.searchResults定義
  └─ displayResults関数の定義（AttendanceSystem.Search.displayResultsを呼び出し）
  └─ イベントリスナーの設定
```

---

## 🎯 推奨される対応順序

### フェーズ1: 即座に対応（緊急度: 高）

1. **グローバル関数の名前空間化**
   - `attendance-check.js`のグローバル関数を`AttendanceSystem.Check`名前空間に移動
   - `search.html`の関数を`AttendanceSystem.Search`名前空間に統一

2. **関数の重複定義の解消**
   - `timeToMinutes`関数を1つに統一（`attendance-common.js`に移動）

3. **DOMContentLoadedの統一**
   - フォーム送信リスナーを`DOMContentLoaded`の外で直接設定（動作していた状態に戻す）

### フェーズ2: 短期対応（1-2週間）

4. **テンプレートファイルの統一**
   - `templates/search.html`と`templates_dev/search.html`を統一
   - 自動同期スクリプトの導入

5. **グローバル変数の統一**
   - `searchResults`を`AttendanceSystem.Data.searchResults`に統一
   - `allEmployees`を`AttendanceSystem.Data.employees`に統一

### フェーズ3: 中期対応（1ヶ月）

6. **APIエンドポイントの分離**
   - `/api/search`と`/api/search/alerts`に分離
   - フロントエンドの修正

### フェーズ4: 長期対応（継続的改善）

7. **コードのリファクタリング**
   - 関数の責務を明確化
   - テストコードの追加
   - ドキュメントの整備

---

## 📝 チェックリスト

### 修正前の確認事項

- [ ] どの関数がグローバルスコープで定義されているか確認
- [ ] どの関数が名前空間内で定義されているか確認
- [ ] スクリプトの読み込み順序を確認
- [ ] 関数の呼び出し元を確認
- [ ] 環境間の差異を確認
- [ ] Git履歴で「いつから動かなくなったか」を特定

### 修正時の注意事項

- [ ] 関数の名前空間化は段階的に実施
- [ ] 既存のコードとの互換性を維持
- [ ] 他のページへの影響を確認
- [ ] テストを実施してから本番環境に反映
- [ ] **5000と5001の両方の環境で動作確認**
- [ ] **変更前にユーザーの明示的な許可を得る**

### 修正後の確認事項

- [ ] 検索機能が正常に動作するか確認
- [ ] エラー・警告が正しく表示されるか確認
- [ ] 環境間で動作が一致するか確認
- [ ] パフォーマンスに問題がないか確認
- [ ] ブラウザキャッシュをクリアして再確認

---

## 🔗 関連ファイル

- `work_attend_server/server/api_attendance.py`: 検索APIエンドポイント
- `work_attend_server/server/attendance_check_service.py`: エラー・警告判定ロジック
- `work_attend_server/server/templates/search.html`: 5000用検索画面テンプレート
- `work_attend_server/server/templates_dev/search.html`: 5001用検索画面テンプレート
- `work_attend_server/server/static/js/attendance-check.js`: 検索機能のJavaScript
- `work_attend_server/server/static/js/attendance-common.js`: 共通JavaScriptライブラリ
- `work_attend_server/server/static/js/api-service.js`: APIサービス
- `work_attend_server/server/static/js/employee-list.js`: 従業員リスト管理
- `work_attend_server/server/DOCKER_COMPOSE_DIFF.md`: 5000と5001の環境差異

---

## 🚫 再発防止策

### 1. コード変更前の原則

**変更を行う前に、必ず以下を確認する**:

- [ ] 変更の目的と理由が明確か
- [ ] 影響を受ける可能性のあるファイルと環境をリストアップしたか
- [ ] 5000と5001の両方の環境で動作することを確認したか
- [ ] 既存の機能に影響がないことを確認したか
- [ ] エラーケースを考慮したか
- [ ] 変更後の動作確認方法を明確にしたか
- [ ] **ユーザーから明示的な実行許可を得たか**

### 2. 変更後の原則

**変更を行った後、必ず以下を確認する**:

- [ ] 変更内容をドキュメントに記録したか
- [ ] 5000と5001の両方の環境で動作確認を行ったか
- [ ] エラーケースもテストしたか
- [ ] 環境間の同期が取れているか
- [ ] 既存の機能が正常に動作することを確認したか

### 3. 問題発生時のアプローチ

**問題が発生した場合、以下を実施する**:

1. **問題の記録**: 問題の詳細を記録する
2. **根本原因の分析**: なぜこの問題が発生したのかを分析する
3. **影響範囲の確認**: この問題が他の機能に影響を与えていないか確認する
4. **解決策の検討**: 根本原因を解決するための対策を検討する
5. **再発防止策の検討**: 同じ問題が繰り返し発生しないようにするための対策を検討する
6. **比較可能なものがあれば比較する**: 動作している環境と動作していない環境を比較

### 4. 定期的なレビュー

**定期的に以下をレビューする**:

- 同じ問題が繰り返し発生していないか
- 作成したドキュメントが実際の作業で活用されているか
- 改善提案が実装されているか

### 5. AIコーディングの問題点への対策

**AIがコードを生成する際の注意事項**:

- ❌ **許可なくコードを変更しない**
- ❌ **「検証コードを生成」と言われただけで、メインコードベースを修正しない**
- ❌ **デバッグ結果を見て「これは修正すべき」と判断して勝手に修正しない**
- ❌ **「問題を確認した」と言われただけで、自動的に修正を開始しない**
- ✅ **変更前には必ずユーザーの明示的な許可を得る**
- ✅ **2回失敗したら手法を変える**
- ✅ **比較できるものがあれば比較する**

---

## 📌 まとめ

### 問題の根本原因

1. グローバル関数の競合
2. スクリプトの読み込み順序への依存
3. APIエンドポイントの過度な依存
4. 環境間の差異
5. 関数の重複定義
6. DOMContentLoadedイベントリスナーの問題
7. attendance-common.jsの読み込み問題

### 解決策の優先順位

1. グローバル関数の名前空間化（最優先）
2. DOMContentLoadedの統一
3. 関数の重複定義の解消
4. テンプレートファイルの統一
5. APIエンドポイントの分離

### 今後の注意事項

- 新しい関数を追加する場合は、必ず名前空間内に定義する
- グローバルスコープへの関数定義を避ける
- 環境間の同期を自動化する
- 変更前には影響範囲を確認する
- **コード変更前には必ずユーザーの明示的な許可を得る**
- **2回失敗したら手法を変える**
- **比較できるものがあれば比較する**

---

**作成者**: AI Assistant  
**最終更新**: 2026年1月29日  
**統合元**: 複数の検索機能関連ドキュメントを統合
