# エラー診断ガイド

## 🔍 「通信エラーが発生しました」の診断手順

### 1. ブラウザのコンソールを確認

1. **F12**キーを押してデベロッパーツールを開く
2. **Console**タブを選択
3. 表示されているエラーメッセージを確認：

#### エラーパターン別の対処法

**パターンA: `Failed to fetch`**
```
POST Error details: TypeError: Failed to fetch
```
→ **原因**: サーバーが起動していない、またはポート番号が違う
→ **対処**: 
  - サーバーのターミナルで`python "medicine recomend/app.py"`が実行中か確認
  - URLが`http://localhost:5000`であることを確認

**パターンB: `Server error: 500 Internal Server Error`**
```
POST failed: 500 Internal Server Error
```
→ **原因**: サーバー側でエラーが発生している
→ **対処**:
  - サーバーのターミナルでエラーログを確認
  - 赤いエラーメッセージ（Traceback）を探す

**パターンC: `SyntaxError: Unexpected token`**
```
SyntaxError: Unexpected token '<' in JSON at position 0
```
→ **原因**: サーバーがHTMLを返している（JSONではない）
→ **対処**:
  - サーバーが正しくJSONを返しているか確認
  - `app.py`の770-779行目のJSON返却処理を確認

**パターンD: `CORS error`**
```
Access to fetch at '...' has been blocked by CORS policy
```
→ **原因**: クロスオリジン制限
→ **対処**:
  - 同じブラウザで`http://localhost:5000`を開いているか確認

### 2. ネットワークタブを確認

1. **F12** → **Network**タブを選択
2. メッセージを送信
3. POSTリクエストを見つける
4. クリックして詳細を確認：

**確認項目**:
- **Status**: `200 OK`であるべき
- **Response**: JSONデータが返ってきているか
- **Headers**: `Content-Type: application/json`であるか

### 3. サーバーログを確認

サーバーのターミナルで以下を確認：

**正常な場合**:
```
📨 POST処理開始
📝 受信メッセージ: のどが痛いです
💾 メッセージ保存完了: 2 messages
✅ POST処理完了 - JSON返却: 2 messages
127.0.0.1 - - [01/Oct/2025 05:26:47] "POST /?v=... HTTP/1.1" 200 -
```

**エラーの場合**:
```
Traceback (most recent call last):
  File "...", line ..., in ...
    ...
Error: ...
127.0.0.1 - - [01/Oct/2025 05:26:47] "POST /?v=... HTTP/1.1" 500 -
```

### 4. 一般的な解決方法

#### 解決策1: サーバー再起動
```powershell
# 現在のサーバーを停止（Ctrl+C）
# 再起動
python "medicine recomend/app.py"
```

#### 解決策2: ブラウザキャッシュクリア
```
Ctrl + Shift + R（完全リロード）
```

#### 解決策3: ポート確認
```powershell
# ポート5000が使用中か確認
netstat -ano | findstr :5000
```

#### 解決策4: 別のブラウザで試す
- Chrome
- Firefox
- Edge

### 5. 詳細デバッグ

ブラウザコンソールに表示される新しいログ：
```javascript
POST response status: 200 OK  // ステータス確認
POST response: {status: "ok", message_count: 2}  // レスポンス内容
Session data received (attempt 1): {...}  // セッションデータ
Messages count: 2  // メッセージ数
✓ All messages loaded, rendering...  // 描画開始
```

エラーの場合：
```javascript
POST Error details: TypeError: ...
Error name: TypeError
Error message: Failed to fetch
Error stack: TypeError: Failed to fetch at ...
```

### 6. 緊急対処

すべて試しても解決しない場合：

1. **セッションクリア**
   ```javascript
   // ブラウザコンソールで実行
   localStorage.clear();
   sessionStorage.clear();
   location.reload();
   ```

2. **新しいブラウザタブで開く**
   - シークレットモード/プライベートモードで試す

3. **サーバーログ全体を確認**
   - エラーメッセージをすべてコピーして原因を特定
