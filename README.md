# 認証 API（FastAPI）

Vue + Nginx + 複数 FastAPI 構成のうち、`/api/auth` に配置する **認証専用** の API です。ログイン成功時に JWT を **HttpOnly Cookie** に格納し、`/me` で検証してユーザー情報を返します。

## 前提

- Python 3.10 以上を想定
- PostgreSQL に `public.accounts` テーブルが存在すること（仕様は [API_LOGIN_SPEC.md](./API_LOGIN_SPEC.md)）

## セットアップ

### 1. 仮想環境と依存関係

リポジトリルート（本ファイルと同じ階層）で実行します。

```powershell
cd d:\h\github\m_login
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 環境変数（`.env`）

ルートに `.env` を置きます。初期テンプレートはリポジトリ同梱の `.env` / `.env.example` を参照してください。

主な変数:

| 変数 | 説明 |
|------|------|
| `DB_*` | PostgreSQL 接続（ホスト・ポート・DB 名・ユーザー・パスワード） |
| `SECRET_KEY` | JWT 署名鍵（本番では十分に長いランダム値に変更） |
| `ALGORITHM` | JWT アルゴリズム（例: `HS256`） |
| `CORS_ORIGINS` | 許可するオリジンをカンマ区切り（Vue の URL。IP アクセスなら `http://192.168.x.x:5173` など） |
| `COOKIE_NAME` | （任意）Cookie 名。既定は `access_token` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | （任意）JWT / Cookie の有効期限（分）。既定は `30` |

`.env` の読み込みは `auth_api/app/config.py` の `get_settings()` 経由で行われます（モジュール import 時点でもリポジトリルートの `.env` を参照します）。

### 3. アカウントのパスワードについて

DB の `accounts.password` には **平文ではなく bcrypt ハッシュ** を保存してください。ログイン時に `passlib` で検証します。

開発用にハッシュを生成する例:

```powershell
.\.venv\Scripts\python -c "from auth_api.app.security.password import hash_password; print(hash_password('your-password'))"
```

生成した文字列を `INSERT` / `UPDATE` で `password` 列に保存します。

## 起動方法（開発）

リポジトリルートをカレントにして、`auth_api.app.main:app` を指定します。

```powershell
cd d:\h\github\m_login
.\.venv\Scripts\Activate.ps1
uvicorn auth_api.app.main:app --reload --host 0.0.0.0 --port 8000
```

- ドキュメント: `http://127.0.0.1:8000/docs`
- ヘルスチェック: `GET /health`

## Nginx との関係

本アプリのルートは **`/login` / `/logout` / `/me`** です。リバースプロキシで **`/api/auth/` をこのアプリの `/` に付け替える** 構成を想定しています。

例（概念）:

```nginx
location /api/auth/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

この場合、クライアントからは `POST /api/auth/login` のように呼び出します。Cookie の `Path=/` はオリジン全体に送られるため、`/api/recipe` など別プレフィックスの API にも同じオリジンであれば Cookie が付きます（`SameSite=Lax` の範囲内）。

## Vue からの呼び出し（要点）

- `axios` の `withCredentials: true` を有効にする
- `CORS_ORIGINS` に **実際の Vue のオリジン**（スキーム・ホスト・ポートまで一致）を含める
- HTTPS（またはローカルで `Secure` を満たす環境）を用意する。Cookie は **`Secure`** のため、平文 HTTP ではブラウザが Cookie を送らないことがあります

## 他の FastAPI で JWT を検証する

認証サービスと **同じ** `SECRET_KEY`・`ALGORITHM`・`COOKIE_NAME` を用いて、`auth_api/app/security/jwt_verifier.py` の `JWTVerifier` を利用できます。

```python
from fastapi import Depends, FastAPI, Request
from auth_api.app.security.jwt_verifier import JWTVerifier

verifier = JWTVerifier(secret_key="...", algorithm="HS256", cookie_name="access_token")
require_auth = verifier.dependency()

app = FastAPI()

@app.get("/api/recipe/items")
def list_items(claims: dict = Depends(require_auth)):
    user_id = int(claims["sub"])
    ...
```

別リポジトリに分ける場合は、`jwt_verifier.py` をコピーし、環境変数から鍵を読み込むようにしてください。

## プロジェクト構成（抜粋）

```
m_login/
  .env
  requirements.txt
  README.md
  API_LOGIN_SPEC.md
  auth_api/
    app/
      main.py           # FastAPI 生成・CORS
      config.py         # 設定（.env）
      database.py       # DB セッション
      models.py         # SQLAlchemy モデル
      schemas.py        # Pydantic
      routers/auth.py   # /login /logout /me
      security/
        password.py     # bcrypt
        jwt_tokens.py   # JWT 発行
        jwt_verifier.py # JWT 検証クラス（他サービス向け）
```

詳細な API・DB 仕様は [API_LOGIN_SPEC.md](./API_LOGIN_SPEC.md) を参照してください。
