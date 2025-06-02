# MySNS（仮）

Flaskを使って作成したSNSアプリです。  
ユーザー登録から投稿、DM、フォロー、通知まで、基本的なSNS機能を備えています。

---

## 🔧 主な機能

- ユーザー登録 / ログイン / ログアウト
- プロフィール画面 / プロフィール編集（画像対応）
- 投稿機能（画像付き）
- タイムライン表示
- いいね / コメント機能
- フォロー / フォロワー機能
- ダイレクトメッセージ（DM）機能
- 通知機能（いいね・コメント・フォロー）

---

## 📁 ディレクトリ構成
my-sns-app/

├── app.py

├── static/

│ └── uploads/ ← 画像アップロード用（※空でも必要）

├── templates/ ← HTMLテンプレート群

├── requirements.txt

├── .gitignore

└── README.md


## 🚀 セットアップ手順

1. 仮想環境の作成（任意）
   
bash

python -m venv venv

source venv/bin/activate  # Windowsの場合: venv\Scripts\activate



2. ライブラリのインストール

bash

pip install -r requirements.txt


3.アプリの起動

python app.py


4.ブラウザでアクセス

例:http://localhost:5000/register


## 🛠 使用技術

Python 3.x

Flask

SQLite3

HTML / CSS / JavaScript

Jinja2



## 補足


現状はローカル環境での動作を想定しています。

.envによる環境変数管理や、本番用設定の追加も今後検討しています。

このアプリは個人の学習のために作成しました。
