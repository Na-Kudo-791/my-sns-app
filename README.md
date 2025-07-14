# MySNS: 高機能なSNSアプリケーション

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)  
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)  
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/index.html)  
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/ja/docs/Web/Guide/HTML/HTML5)  
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/ja/docs/Web/CSS)  
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/ja/docs/Web/JavaScript)

FlaskとSQLiteを使って構築した、多機能かつスケーラブルなSNSアプリケーションです。  
認証・画像投稿・DM・通知・ハッシュタグ機能など、実際のサービスを意識した構成で、Python・Web開発の学習成果を形にしました。

---

## ✨ 主な機能

### 1. アカウント管理
- **ユーザー登録 / ログイン / ログアウト**
- **メールによる本人確認（登録時）**
- **パスワードリセット機能（メール連携）**
- **プロフィール編集（表示名・自己紹介・画像）**

![プロフィール画面](images/profile.png)  
![編集画面](images/edit_profile.png)

---

### 2. 投稿・インタラクション
- **投稿機能（テキスト＋画像）**
- **非同期「いいね」・フォロー（Fetch API使用）**
- **コメント機能**

![タイムライン](images/timeline.png)

---

### 3. ユーザー間コミュニケーション
- **ダイレクトメッセージ（DM）：1対1のプライベートチャット**
- **リアルタイム通知（フォロー・いいね・コメント）**
- **ハッシュタグ機能：#タグ自動リンク＋タグ一覧表示**

---

## 🛠 使用技術

- **Python 3.x**：主要ロジック
- **Flask**：軽量なWebフレームワーク
- **SQLite3 + FTS5**：全文検索付きローカルDB
- **HTML / CSS / JavaScript**：UI/UX構築
- **Jinja2**：テンプレートエンジン
- **Bootstrap 5**：フロントエンドデザイン
- **Fetch API**：非同期通信


---

## 🚀 セットアップ手順

1.**リポジトリをクローン**
```bash
git clone https://github.com/your-username/my-sns-project.git
cd my-sns-project

2. **仮想環境の作成**
```bash
python -m venv venv
source venv/bin/activate  # Windowsなら .\venv\Scripts\activate

3. **依存ライブラリのインストール**
```bash
pip install -e .

4. **.envの作成**
```bash
SECRET_KEY='your-generated-secret-key'
MAIL_SERVER='smtp.gmail.com'
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME='your-email@gmail.com'
MAIL_PASSWORD='your-app-password'

5. **データベースの初期化**
```bash
flask --app src/my_sns_app init-db

6. **アプリケーション起動**
```bash
flask --app src/my_sns_app run


7. **ブラウザでアクセス**
```bash
http://localhost:5000/


💡 今後の展望 / 改善予定
フォローベースのタイムライン表示

CSRF対策の強化（Flask-WTF）

SQLAlchemyによるORM化

pytestによる自動テストの追加

Gunicorn / Dockerでの本番環境構築
