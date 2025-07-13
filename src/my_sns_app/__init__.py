import os
import re  # 正規表現を扱うために追加
from flask import Flask
from dotenv import load_dotenv
from flask_mail import Mail

mail = Mail()

# --- ここから追加：ハッシュタグをリンクに変換するフィルタ関数 ---
def linkify_hashtags(text):
    # #ハッシュタグ というパターンの文字列を<a href="/hashtag/ハッシュタグ">#ハッシュタグ</a>というHTMLリンクに置換する
    return re.sub(r'#(\w+)', r'<a href="/hashtag/\1">#\1</a>', text)
# --- ここまで追加 ---

def create_app(test_config=None):
    app = Flask(__name__,
                instance_relative_config=True,
                template_folder='../../templates',
                static_folder='../../static')

    load_dotenv()

    # (Mailの設定は変更なし)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
    mail.init_app(app)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.path.join(app.instance_path, 'database.db'),
    )

    UPLOAD_FOLDER = 'uploads'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, UPLOAD_FOLDER)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- ここから追加：カスタムフィルタをJinja2環境に登録 ---
    app.jinja_env.filters['linkify'] = linkify_hashtags
    # --- ここまで追加 ---

    from . import db
    db.init_app(app)

    from . import auth, user, post, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(post.bp)
    app.register_blueprint(main.bp)
    
    app.add_url_rule('/', endpoint='main.timeline')

    return app