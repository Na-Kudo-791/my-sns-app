import functools
import random
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message

from my_sns_app.db import get_db
from my_sns_app import mail

bp = Blueprint('auth', __name__)

# --- トークン生成・検証ヘルパー関数 ---

def generate_confirmation_token(email):
    """メール確認用のトークンを生成する"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirmation-salt')

def confirm_token(token, expiration=3600):
    """メール確認用のトークンを検証する（有効期限：1時間）"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt='email-confirmation-salt',
            max_age=expiration
        )
    except Exception:
        return False
    return email

def generate_password_reset_token(email):
    """パスワードリセット用のトークンを生成する"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')

def confirm_password_reset_token(token, expiration=3600):
    """パスワードリセット用のトークンを検証する（有効期限：1時間）"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except Exception:
        return False
    return email


# --- 認証ルート ---

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        
        if not email or not password:
            flash("メールアドレスとパスワードは必須です。", "error")
            return redirect(url_for('auth.register'))

        try:
            random_number = random.randint(10000, 99999)
            username = f"user{random_number}"
            db.execute(
                "INSERT INTO users (username, email, password, is_confirmed) VALUES (?, ?, ?, 0)",
                (username, email, generate_password_hash(password)),
            )
            db.commit()

            # 確認メールを送信
            token = generate_confirmation_token(email)
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            html = render_template('email/activate.html', confirm_url=confirm_url)
            subject = "【My SNS】ご登録ありがとうございます。メールアドレスの確認をお願いします。"
            msg = Message(subject, recipients=[email], html=html)
            mail.send(msg)

            flash('ご登録ありがとうございます。確認メールを送信しましたので、メール内のリンクをクリックして登録を完了してください。', 'info')
            return redirect(url_for("auth.login"))

        except db.IntegrityError:
            flash("このメールアドレスは既に使用されています。", "error")
        
    return render_template('register.html')

@bp.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('確認リンクが無効か、有効期限が切れています。', 'danger')
        return redirect(url_for('auth.login'))
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if not user:
        flash('ユーザーが見つかりませんでした。', 'danger')
        return redirect(url_for('auth.login'))

    if user['is_confirmed']:
        flash('アカウントはすでに有効化されています。', 'success')
    else:
        db.execute('UPDATE users SET is_confirmed = 1 WHERE email = ?', (email,))
        db.commit()
        flash('アカウントを有効化しました。ログインしてください。', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and not user['is_confirmed']:
            flash('アカウントが有効化されていません。お送りしたメールをご確認ください。')
            return redirect(url_for('auth.login'))

        if user is None or not check_password_hash(user['password'], password):
            flash("メールアドレスまたはパスワードが間違っています。")
        else:
            session.clear()
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('user.profile'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            token = generate_password_reset_token(email)
            reset_url = url_for('auth.reset_with_token', token=token, _external=True)
            html = render_template('email/reset_password.html', reset_url=reset_url)
            subject = "【My SNS】パスワードリセットのご案内"
            msg = Message(subject, recipients=[email], html=html)
            mail.send(msg)
            flash('パスワードリセット用のメールを送信しました。', 'info')
        else:
            flash('そのメールアドレスは登録されていません。', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('auth/request_reset.html')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    email = confirm_password_reset_token(token)
    if not email:
        flash('パスワードリセットのリンクが無効か、有効期限が切れています。', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form['password']
        db = get_db()
        db.execute(
            'UPDATE users SET password = ? WHERE email = ?',
            (generate_password_hash(password), email)
        )
        db.commit()
        flash('パスワードを更新しました。新しいパスワードでログインしてください。', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_with_token.html')


# --- ログイン状態を管理するヘルパー関数 ---

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view