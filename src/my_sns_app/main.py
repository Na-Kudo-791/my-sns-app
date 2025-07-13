from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from my_sns_app.db import get_db
from my_sns_app.auth import login_required

# Blueprintの作成
bp = Blueprint('main', __name__)

# タイムラインのルート
@bp.route('/')
@bp.route('/timeline')
def timeline():
    """
    タイムラインページを表示します。
    ログインしている場合はフォロー中のユーザーと自分の投稿を、
    未ログインの場合は全ユーザーの投稿を表示します。
    """
    db = get_db()
    
    # ログイン状態に応じて表示する投稿を切り替える
    if g.user:
        # フォローしているユーザーと自分のuser_idを取得
        posts = db.execute('''
            SELECT p.id, p.content, p.image, p.created_at, p.user_id, u.username, u.display_name, u.profile_image,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
            FROM posts p JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id IN (SELECT followed_id FROM follows WHERE follower_id = ?) OR p.user_id = ?
            ORDER BY p.created_at DESC
        ''', (g.user['user_id'], g.user['user_id'])).fetchall()
    else:
        # 全ての投稿を取得
        posts = db.execute('''
            SELECT p.id, p.content, p.image, p.created_at, p.user_id, u.username, u.display_name, u.profile_image,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
            FROM posts p JOIN users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
        ''').fetchall()
    
    # 各投稿に対するコメントを取得
    comments_dict = {}
    for post in posts:
        comments = db.execute('''
            SELECT c.content, u.username
            FROM comments c JOIN users u ON c.user_id = u.user_id
            WHERE c.post_id = ? ORDER BY c.created_at ASC
        ''', (post['id'],)).fetchall()
        comments_dict[post['id']] = comments

    # ログインユーザーがいいねした投稿のIDセットを取得
    liked_posts = set()
    if g.user:
        likes = db.execute('SELECT post_id FROM likes WHERE user_id = ?', (g.user['user_id'],)).fetchall()
        liked_posts = {row['post_id'] for row in likes}

    return render_template('timeline.html', posts=posts, liked_posts=liked_posts, comments_dict=comments_dict)

# ダイレクトメッセージのルート
@bp.route('/message/<int:receiver_id>', methods=['GET', 'POST'])
@login_required
def message(receiver_id):
    """ダイレクトメッセージの送受信ページ"""
    db = get_db()
    receiver = db.execute("SELECT * FROM users WHERE user_id = ?", (receiver_id,)).fetchone()
    if not receiver:
        flash("宛先のユーザーが見つかりません。")
        return redirect(url_for('main.timeline'))

    if request.method == 'POST':
        content = request.form['content']
        if content:
            db.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
                       (g.user['user_id'], receiver_id, content))
            db.commit()
            flash("メッセージを送信しました。")
            return redirect(url_for('main.message', receiver_id=receiver_id))

    messages = db.execute('''
        SELECT * FROM messages WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at
    ''', (g.user['user_id'], receiver_id, receiver_id, g.user['user_id'])).fetchall()

    return render_template('message.html', messages=messages, receiver=receiver)

# 受信箱のルート
@bp.route('/inbox')
@login_required
def inbox():
    """メッセージのやり取りがある相手の一覧ページ"""
    db = get_db()
    user_id = g.user['user_id']
    conversations = db.execute('''
        SELECT u.user_id, u.username, u.display_name, u.profile_image FROM users u JOIN (
            SELECT DISTINCT
                CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS other_user_id
            FROM messages
            WHERE sender_id = ? OR receiver_id = ?
        ) conv ON u.user_id = conv.other_user_id WHERE u.user_id != ?
    ''', (user_id, user_id, user_id, user_id)).fetchall()

    return render_template('inbox.html', conversations=conversations)

# 通知一覧のルート
@bp.route('/notifications')
@login_required
def notifications():
    """通知一覧ページ"""
    db = get_db()
    user_id = g.user['user_id']
    notifs = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    
    # 通知を既読にする
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
    db.commit()

    return render_template("notifications.html", notifications=notifs)

# 検索機能のルート
@bp.route('/search')
def search():
    """投稿とユーザーの検索機能"""
    query = request.args.get('q')
    if not query:
        return redirect(url_for('main.timeline'))

    # FTS5は特殊文字をそのまま扱うとエラーになるため、
    # クエリ全体をダブルクォートで囲んでフレーズ検索として扱う
    fts_query = f'"{query}"'

    db = get_db()
    
    # 全文検索(FTS5)を使って投稿を検索
    found_posts = db.execute('''
        SELECT p.*, u.username, u.display_name, u.profile_image
        FROM posts p 
        JOIN users u ON p.user_id = u.user_id
        JOIN posts_fts fts ON p.id = fts.rowid
        WHERE posts_fts MATCH ?
        ORDER BY rank
    ''', (fts_query,)).fetchall()

    # ユーザー名は通常通りLIKEで検索
    search_query = f"%{query}%"
    found_users = db.execute(
        "SELECT * FROM users WHERE username LIKE ? OR display_name LIKE ?",
        (search_query, search_query)
    ).fetchall()

    return render_template('search_results.html', query=query, posts=found_posts, users=found_users)

# ハッシュタグ検索のルート
@bp.route('/hashtag/<string:tag_name>')
def hashtag(tag_name):
    """ハッシュタグに関連する投稿を一覧表示する"""
    db = get_db()
    
    posts = db.execute('''
        SELECT p.id, p.content, p.image, p.created_at, p.user_id, u.username, u.display_name, u.profile_image,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        FROM posts p
        JOIN users u ON p.user_id = u.user_id
        JOIN post_hashtags ph ON p.id = ph.post_id
        JOIN hashtags h ON ph.hashtag_id = h.id
        WHERE h.name = ?
        ORDER BY p.created_at DESC
    ''', (tag_name,)).fetchall()
    
    # 各投稿のコメントを取得
    comments_dict = {}
    for post in posts:
        comments = db.execute('''
            SELECT c.content, u.username
            FROM comments c JOIN users u ON c.user_id = u.user_id
            WHERE c.post_id = ? ORDER BY c.created_at ASC
        ''', (post['id'],)).fetchall()
        comments_dict[post['id']] = comments

    # ログインユーザーがいいねした投稿のIDセットを取得
    liked_posts = set()
    if g.user:
        likes = db.execute('SELECT post_id FROM likes WHERE user_id = ?', (g.user['user_id'],)).fetchall()
        liked_posts = {row['post_id'] for row in likes}

    # タイムライン用のテンプレートを再利用して結果を表示
    return render_template('timeline.html', posts=posts, liked_posts=liked_posts, hashtag_name=tag_name, comments_dict=comments_dict)
