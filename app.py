from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import random
import imghdr

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 新規登録画面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        c = conn.cursor()

        # 自動生成された username
        random_number = random.randint(10000, 99999)
        username = f"user{random_number}"

        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("このメールアドレスは既に使用されています。", "error")
            return redirect(url_for('register'))
        finally:
            conn.close()

        flash("登録が完了しました。ログインしてください。", "success")
        return redirect(url_for('login'))
    return render_template('register.html')


#ログイン画面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT user_id, username, password FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']  # ← ここを追加
            return redirect(url_for('profile'))

        flash("メールアドレスまたはパスワードが間違っています。")
    return render_template('login.html')


# プロフィール画面
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
    posts = conn.execute('SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    followers = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (session['user_id'],)).fetchone()[0]
    following = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (session['user_id'],)).fetchone()[0]

    conn.close()  

    return render_template('profile.html',
                           username=user['username'],
                           user_id=user['user_id'],
                           display_name=user['display_name'],
                           bio=user['bio'],
                           profile_image=user['profile_image'],
                           posts=posts,
                           followers=followers,
                           following=following)


#自分以外のユーザー プロフィール画面
@app.route('/user/<int:user_id>', endpoint='user_profile')
def user_profile(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if not user:
        conn.close()
        return "ユーザーが見つかりませんでした", 404

    posts = conn.execute("SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    followers = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,)).fetchone()[0]
    following = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,)).fetchone()[0]

    is_self = ('user_id' in session) and (session['user_id'] == user_id)  # ← 自分かどうか判定

    is_following = False
    if not is_self and 'user_id' in session:
        follow = conn.execute('''
            SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?
        ''', (session['user_id'], user_id)).fetchone()
        is_following = follow is not None

    conn.close()

    return render_template('user_profile.html',
                           username=user['username'],
                           user_id=user['user_id'],
                           display_name=user['display_name'],
                           bio=user['bio'],
                           profile_image=user['profile_image'],
                           posts=posts,
                           followers=followers,
                           following=following,
                           is_self=is_self,
                           is_following=is_following)



#  プロフィール変更画面
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        display_name = request.form['display_name']
        username = request.form['username']
        bio = request.form['bio']


        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_image = filename

        if profile_image:
            conn.execute("UPDATE users SET username = ?, display_name = ?, bio = ?, profile_image = ? WHERE user_id = ?",
                 (username, display_name, bio, profile_image, session['user_id']))
        else:
            conn.execute("UPDATE users SET username = ?, display_name = ?, bio = ? WHERE user_id = ?",
                 (username, display_name, bio, session['user_id']))

        conn.commit()
        conn.close()
        return redirect(url_for('profile'))

    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user)

# ポスト作成画面
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
         
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        image = None

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename

        if len(content) > 200:
            return "投稿文は200文字以内にしてください。"

        conn = get_db_connection()
        conn.execute("INSERT INTO posts (user_id, content, image) VALUES (?, ?, ?)",
                     (session['user_id'], content, image))
        conn.commit()
        conn.close()
        return redirect(url_for('profile'))

    return render_template('create_post.html')

#タイムライン画面
@app.route('/timeline')
def timeline():
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT posts.*, users.username, users.profile_image
        FROM posts
        JOIN users ON posts.user_id = users.user_id
        ORDER BY posts.created_at DESC
    ''').fetchall()

    comments_dict = {}
    likes_dict = {}
    liked_by_user = {}

    for post in posts:
        post_id = post['id']
        comments = conn.execute('''
            SELECT comments.*, users.username
            FROM comments
            JOIN users ON comments.user_id = users.user_id
            WHERE post_id = ?
            ORDER BY created_at ASC
        ''', (post_id,)).fetchall()
        comments_dict[post_id] = comments

        like_count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]
        likes_dict[post_id] = like_count

        if 'user_id' in session:
            liked = conn.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?", (post_id, session['user_id'])).fetchone()
            liked_by_user[post_id] = liked is not None
        else:
            liked_by_user[post_id] = False

    conn.close()
    return render_template('timeline.html',
                           posts=posts,
                           comments_dict=comments_dict,
                           likes_dict=likes_dict,
                           liked_by_user=liked_by_user)
#　ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ポスト削除
@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("投稿を削除しました。")
    return redirect(url_for('profile'))


#　ポストへのコメント
@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    content = request.form['comment']
    if not content:
        flash('コメントが空です。')
        return redirect(request.referrer)

    user_id = session['user_id']
    username = session.get('username')  # 通知用にユーザー名を取得

    conn = get_db_connection()
    cursor = conn.cursor()

    # コメントを保存
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (post_id, user_id, content)
    )

    # 投稿の作成者を取得
    post_author = cursor.execute(
        "SELECT user_id FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    if post_author:
        post_author_id = post_author['user_id']

        # 自分の投稿でなければ通知を追加
        if post_author_id != user_id and username:
            message = f"{username}さんがあなたの投稿にコメントしました。"
            cursor.execute(
                "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                (post_author_id, message)
            )

    conn.commit()
    conn.close()
    return redirect(request.referrer)

# フォロー機能
@app.route('/follow/<int:user_id>', methods=['POST'])
def follow(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    follower_id = session['user_id']
    follower_name = session.get('username')  # 通知用にユーザー名を取得

    if follower_id == user_id:
        flash("自分自身をフォローすることはできません。")
        return redirect(request.referrer)

    conn = get_db_connection()
    cursor = conn.cursor()

    # フォロー済みかチェック
    exists = cursor.execute(
        "SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?",
        (follower_id, user_id)
    ).fetchone()

    if exists:
        flash("すでにフォローしています。")
    else:
        # フォローを登録
        cursor.execute(
            "INSERT INTO follows (follower_id, followed_id) VALUES (?, ?)",
            (follower_id, user_id)
        )

        # 通知を作成（自分自身でなければ）
        if follower_name:
            message = f"{follower_name}さんがあなたをフォローしました。"
            cursor.execute(
                "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                (user_id, message)
            )

        conn.commit()
        flash("フォローしました。")

    conn.close()
    return redirect(request.referrer)

#フォロー解除
@app.route('/unfollow/<int:user_id>', methods=['POST'])
def unfollow(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM follows WHERE follower_id = ? AND followed_id = ?", (session['user_id'], user_id))
    conn.commit()
    conn.close()
    flash("フォローを解除しました。")
    return redirect(request.referrer)


#いいね機能
@app.route('/like/<int:post_id>', methods=['POST'])
def like(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    liked = cursor.execute("SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?", (session['user_id'], post_id)).fetchone()

    if not liked:
        cursor.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (session['user_id'], post_id))

        post_author = cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post_author:
            post_author_id = post_author['user_id']
            if post_author_id != session['user_id']:
                username = session.get('username', '誰か')  # ← 安全に取得
                message = f"{username}さんがあなたの投稿にいいねしました。"
                cursor.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (post_author_id, message))

        conn.commit()

    conn.close()
    return redirect(request.referrer)


#いいね解除
@app.route('/unlike/<int:post_id>', methods=['POST'])
def unlike(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (session['user_id'], post_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

#DM送信画面
@app.route('/message/<int:receiver_id>', methods=['GET', 'POST'])
def message(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        content = request.form['content']
        sender_id = session['user_id']
        conn.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
                     (sender_id, receiver_id, content))
        conn.commit()
        flash("メッセージを送信しました。")

    # 送受信メッセージ取得
    user_id = session['user_id']
    messages = conn.execute('''
        SELECT * FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at
    ''', (user_id, receiver_id, receiver_id, user_id)).fetchall()

    receiver = conn.execute("SELECT * FROM users WHERE user_id = ?", (receiver_id,)).fetchone()
    conn.close()

    return render_template('message.html', messages=messages, receiver=receiver)

#DM受信画面
@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    c = conn.cursor()

    # 自分宛・自分発のやり取りで、自分→自分以外を対象に、相手のID一覧を取得
    c.execute('''
        SELECT DISTINCT
            CASE
                WHEN sender_id = ? THEN receiver_id
                WHEN receiver_id = ? THEN sender_id
            END AS other_user_id
        FROM messages
        WHERE (sender_id = ? OR receiver_id = ?)
          AND NOT (sender_id = ? AND receiver_id = ?)
    ''', (user_id, user_id, user_id, user_id, user_id, user_id))

    other_user_ids = [row['other_user_id'] for row in c.fetchall()]

    # 重複を削除（安全策）
    other_user_ids = list(set(other_user_ids))

    # 相手のプロフィール情報を取得
    conversations = []
    for other_id in other_user_ids:
        c.execute('SELECT user_id, username, display_name FROM users WHERE user_id = ?', (other_id,))
        user = c.fetchone()
        if user:
            conversations.append(user)

    conn.close()
    return render_template('inbox.html', conversations=conversations)

#通知機能
@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()

    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (session['user_id'],)
    )
    conn.commit()
    conn.close()

    return render_template("notifications.html", notifications=notifs)



if __name__ == '__main__':
    app.run(debug=True)
