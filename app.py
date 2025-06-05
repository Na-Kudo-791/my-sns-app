from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import random
import imghdr

# オブジェクトを生成
app = Flask(__name__)

# 秘密鍵(本来は環境変数などで管理する)
app.secret_key = 'your_secret_key'

# アップロードされたファイルstaic/uploadに
UPLOAD_FOLDER = 'static/uploads'
#ない場合自動生成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#Flaskアプリケーションにパス登録
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#データベースに接続する処理
#SQLLite3 軽量データベース管理システム
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 新規登録画面
@app.route('/register', methods=['GET', 'POST'])
def register():
    #フォームが送信されたときフォームからメアド、パスワードを取得
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password) # ハッシュ化

        #データベース接続、カーソルの取得
        conn = get_db_connection()
        c = conn.cursor()

        # username自動生成
        random_number = random.randint(10000, 99999)
        username = f"user{random_number}"

        #データベースに情報を挿入
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, hashed_password))
            conn.commit()
            
        #同じメールアドレスが登録されているとき
        except sqlite3.IntegrityError:
            flash("このメールアドレスは既に使用されています。", "error")
            return redirect(url_for('register'))
            
        finally:
            conn.close() #データベース接続解除

        #登録処理完了時
        flash("登録が完了しました。ログインしてください。", "success")
        return redirect(url_for('login')) # ログイン画面へ
    return render_template('register.html')


#ログイン画面
@app.route('/login', methods=['GET', 'POST'])
def login():
    #フォームが送信されたときメアドとパスワードを取得
    #データベース情報に接続
    #メールアドレスを基にユーザー情報を取得
    #データベース接続閉じる
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT user_id, username, password FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        # userが存在し（つまりメールアドレスが登録されており）、
        # かつcheck_password_hash()関数で入力パスワードと保存されたハッシュ化パスワードが一致すれば認証成功
        # sessionにuser_idとusernameを保存
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username'] 
            return redirect(url_for('profile'))# プロフィールへ
        # flash()関数でエラーメッセージを表示
        flash("メールアドレスまたはパスワードが間違っています。")
    return render_template('login.html')

#　ログアウト
@app.route('/logout')
def logout():
    #　セッションのクリア
    session.clear()
    return redirect(url_for('login')) # ログイン画面へ

# プロフィール画面
@app.route('/profile')
def profile():
     # ログイン状態の確認
    # ユーザーがログインしていなければ、ログインページにリダイレクトする
    # これにより、未認証のユーザーのプロフィールページへのアクセスを防止
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # データベース接続の確立
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()
     
    # ユーザーの投稿一覧を取得
    # ログイン中のユーザーが投稿した全ての記事を、新しい順に取得
    posts = conn.execute('SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    
    # フォロワー数とフォロー数を取得
    followers = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (session['user_id'],)).fetchone()[0]
    following = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (session['user_id'],)).fetchone()[0]
     # データベース接続を閉じる
    conn.close()  

    # プロフィールページのテンプレートをレンダリング
    # 取得したユーザー情報、投稿、フォロワー数、フォロー数を 'profile.html' テンプレートに渡して表示
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
    # データベース接続の確立
    conn = get_db_connection()
    # 指定されたuser_idのユーザー情報を取得
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    # ユーザーが存在しない場合のハンドリング
    # もし指定されたuser_idのユーザーが見つからなければ、エラーメッセージとHTTPステータスコード404（Not Found）を返す
    if not user:
        conn.close()
        return "ユーザーが見つかりませんでした", 404

    #ポスト、フォロー数、フォロワー数の表示
    posts = conn.execute("SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    followers = conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,)).fetchone()[0]
    following = conn.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,)).fetchone()[0]

    # 現在のユーザーが、表示しているプロフィールページの持ち主自身かどうかを判定
    is_self = ('user_id' in session) and (session['user_id'] == user_id)  

    
    # フォロー状態の判定
    # 表示しているプロフィールが自分自身のものでなく、かつ自分がログインしている場合に実行
    is_following = False
    if not is_self and 'user_id' in session:
        #フォロー状況をfollowsテーブルで確認
        follow = conn.execute('''
            SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?
        ''', (session['user_id'], user_id)).fetchone()
         # 結果があればis_followingをTrueに設定し、フォローボタンの表示を制御
        is_following = follow is not None
        
    # データベース接続を閉じる
    conn.close()

    # 取得したユーザー情報、投稿、フォロワー数、フォロー数、そしてフォロー状態（is_self, is_following）を
    # 'user_profile.html' テンプレートに渡して表示します。
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
# ログイン状態の確認
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    #データベース接続
    conn = get_db_connection()

    # フォームが送信された場合
    # フォームから新しいプロフィール情報を取得
    if request.method == 'POST':
        display_name = request.form['display_name']
        username = request.form['username']
        bio = request.form['bio']


        profile_image = None
         # プロフィール画像がアップロードされたか確認
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            # ファイルが存在し、ファイル名が空でない場合
            # ファイル名を安全化（ファイル名に不正な文字が含まれていないかチェック）
            # ファイルをサーバーの指定されたアップロードフォルダに保存
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_image = filename

        # データベースのユーザー情報を更新
        # プロフィール画像がアップロードされた場合は、画像パスも更新
        if profile_image:
            conn.execute("UPDATE users SET username = ?, display_name = ?, bio = ?, profile_image = ? WHERE user_id = ?",
                 (username, display_name, bio, profile_image, session['user_id']))
        else:
            conn.execute("UPDATE users SET username = ?, display_name = ?, bio = ? WHERE user_id = ?",
                 (username, display_name, bio, session['user_id']))

        conn.commit() # データベースへの変更を確定
        conn.close()
        return redirect(url_for('profile'))# プロフィールページにリダイレクト

    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (session['user_id'],)).fetchone()
    conn.close()
    
    # プロフィール編集フォームが記述された 'edit_profile.html' テンプレートをユーザーに表示
    # フォームには現在のユーザー情報が初期値として入力される
    return render_template('edit_profile.html', user=user)

# ポスト作成画面
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    # ログイン状態の確認
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        image = None

         # 画像ファイルがアップロードされたか確認
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # ファイル名を安全化
                filename = secure_filename(file.filename)
                # ファイルをサーバーの指定されたアップロードフォルダに保存
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename

        # 投稿文の文字数制限チェック
        # 投稿内容が200文字を超えていたらエラーメッセージ
        if len(content) > 200:
            return "投稿文は200文字以内にしてください。"

        # データベース接続の確立
        # 投稿情報をデータベースに挿入
        # ログイン中のユーザーID、投稿内容、画像パスをpostsテーブルに保存
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

    # 全投稿の取得（投稿者情報もJOINして取得）
    # 'posts' テーブルと 'users' テーブルを結合（JOIN）し、
    # 各投稿（posts.*）に加えて、投稿者のユーザー名（users.username）とプロフィール画像（users.profile_image）も一緒に取得
    # 投稿は新しい順（created_at DESC）に並べ替えられる
    posts = conn.execute('''
        SELECT posts.*, users.username, users.profile_image
        FROM posts
        JOIN users ON posts.user_id = users.user_id
        ORDER BY posts.created_at DESC
    ''').fetchall()

    # コメントと「いいね」情報を格納するための辞書を初期化
    comments_dict = {}
    likes_dict = {}
    liked_by_user = {}

    # 各投稿に対してコメントと「いいね」情報を取得
    # 取得したすべての投稿を一つずつループ処理
    for post in posts:
        post_id = post['id'] # 現在の投稿のIDを取得

        # その投稿のコメント一覧を取得
        # 'comments' テーブルと 'users' テーブルをJOINし、コメント内容とそのコメントをしたユーザー名を取得します。
        # コメントは作成された古い順（created_at ASC）に並び替え
        comments = conn.execute('''
            SELECT comments.*, users.username
            FROM comments
            JOIN users ON comments.user_id = users.user_id
            WHERE post_id = ?
            ORDER BY created_at ASC
        ''', (post_id,)).fetchall()
        comments_dict[post_id] = comments

        # その投稿の「いいね」数を取得
        # 'likes' テーブルから、該当投稿の「いいね」の総数をカウント
        like_count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]
        likes_dict[post_id] = like_count# 辞書に「いいね」数を保存

        # ログインユーザーがその投稿に「いいね」しているかを確認
        if 'user_id' in session:
            # 'likes' テーブルから、ログインユーザーがこの投稿に「いいね」しているレコードがあるかを確認
            liked = conn.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?", (post_id, session['user_id'])).fetchone()
            liked_by_user[post_id] = liked is not None # 結果があればTrue（いいね済み）、なければFalse（いいねしていない）
        else:
            liked_by_user[post_id] = False # ログインしていない場合は、すべての投稿に対して「いいね」していないと見なす

    conn.close()

     # タイムラインページのテンプレートをレンダリング
    # 取得した全投稿、各投稿のコメント、いいね数、ログインユーザーのいいね状況を
    # 'timeline.html' テンプレートに渡して表示
    return render_template('timeline.html',
                           posts=posts,
                           comments_dict=comments_dict,
                           likes_dict=likes_dict,
                           liked_by_user=liked_by_user)


# ポスト削除
@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection

    # 投稿の削除
    # 指定された 'post_id' の投稿を 'posts' テーブルから削除
    # AND user_id = ? の条件があるため、ログイン中のユーザー（session['user_id']）自身の投稿しか削除できない
    conn.execute("DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("投稿を削除しました。") # 削除完了メッセージの表示
    return redirect(url_for('profile'))


#　ポストへのコメント
@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # コメント内容の取得と空チェック
    # フォームからコメントのテキスト内容 ('comment') を取得
    content = request.form['comment']
     # コメントが空だった場合、エラーメッセージを表示し、元のページに戻す
    if not content:
        flash('コメントが空です。')
        return redirect(request.referrer)

    # ログイン中のユーザー情報を取得
    user_id = session['user_id']
    username = session.get('username')  # 通知用にユーザー名を取得

    # データベース接続の確立
    conn = get_db_connection()
    cursor = conn.cursor()

     # コメントをデータベースに保存
    # 'comments' テーブルに、コメントが紐づく投稿ID、コメントしたユーザーID、コメント内容を挿入
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (post_id, user_id, content)
    )

    # 投稿の作成者を取得
     # コメントされた投稿の作者のuser_idを取得(通知を送る相手を特定するため)
    post_author = cursor.execute(
        "SELECT user_id FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    # 投稿の作者が存在する場合、通知を処理
    if post_author:
        post_author_id = post_author['user_id']

        # 自分の投稿でなければ通知を追加
        # コメントしたユーザーが投稿の作者自身ではない場合、かつユーザー名がセッションにあれば通知を作成
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

     # フォローする側のユーザーIDとユーザー名を取得
    follower_id = session['user_id']
    follower_name = session.get('username')  # 通知用にユーザー名を取得

     # 自分自身をフォローしようとした場合のチェック
    # フォローする側とされる側が同じIDの場合、エラーメッセージを表示しリダイレクト
    if follower_id == user_id:
        flash("自分自身をフォローすることはできません。")
        return redirect(request.referrer)

    # データベース接続の確立
    conn = get_db_connection()
    cursor = conn.cursor()

    # フォロー済みかチェック
     # 'follows' テーブルに、既にこのフォロー関係が登録されているかを確認
    exists = cursor.execute(
        "SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?",
        (follower_id, user_id)
    ).fetchone()

    if exists:
        # 既にフォローしている場合、エラーメッセージを表示
        flash("すでにフォローしています。")
    else:
         # フォローをデータベースに登録
        # 'follows' テーブルに、フォローしたユーザーIDとフォローされたユーザーIDを挿入
        cursor.execute(
            "INSERT INTO follows (follower_id, followed_id) VALUES (?, ?)",
            (follower_id, user_id)
        )

        # 通知を作成（自分自身でなければ）
        # フォローしたユーザーのユーザー名が存在する場合、フォローされたユーザーに通知を作成
        if follower_name:
            message = f"{follower_name}さんがあなたをフォローしました。"
            cursor.execute(
                "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                (user_id, message)
            )

        conn.commit()# データベースへの変更を確定（フォローと通知の保存）
        flash("フォローしました。")# 成功メッセージを表示

    conn.close()
    return redirect(request.referrer)

#フォロー解除
@app.route('/unfollow/<int:user_id>', methods=['POST'])
def unfollow(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # フォロー関係をデータベースから削除
    # 'follows' テーブルから、ログイン中のユーザーが指定されたuser_idのユーザーをフォローしているレコードを削除
    conn = get_db_connection()
    conn.execute("DELETE FROM follows WHERE follower_id = ? AND followed_id = ?", (session['user_id'], user_id))
    
    conn.commit()# データベースへの変更を確定
    conn.close()
    
    flash("フォローを解除しました。")# 解除完了メッセージの表示
    return redirect(request.referrer)


#いいね機能
@app.route('/like/<int:post_id>', methods=['POST'])
def like(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # データベース接続の確立とカーソルの取得
    conn = get_db_connection()
    cursor = conn.cursor()

    # 既に「いいね」済みかチェック
    # 現在ログインしているユーザーが、指定された投稿に既に「いいね」をしているかを確認
    liked = cursor.execute("SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?", (session['user_id'], post_id)).fetchone()

    # まだ「いいね」していない場合のみ処理を実行
    if not liked:
        # 「いいね」をデータベースに登録
        # 'likes' テーブルに、いいねしたユーザーIDと投稿IDを挿入
        cursor.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (session['user_id'], post_id))
        # 投稿の作成者を取得
        # いいねされた投稿の作者のuser_idを取得(これは通知を送る相手を特定するため)
        post_author = cursor.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()

        # 投稿の作者が存在し、かつ「いいね」したのが自分自身ではない場合、通知を作成
        if post_author:
            post_author_id = post_author['user_id']
            # 「いいね」したユーザーが投稿の作者自身ではない場合
            if post_author_id != session['user_id']:
                # 通知メッセージに使用するユーザー名を取得します。
                # session.get('username', '誰か') は、usernameがセッションにない場合に「誰か」というデフォルト値を設定する
                username = session.get('username', '誰か')  
                message = f"{username}さんがあなたの投稿にいいねしました。"
                # 'notifications' テーブルに通知を挿入します。
                cursor.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (post_author_id, message))

        conn.commit()# データベースへの変更を確定

    conn.close()
    return redirect(request.referrer)


#いいね解除
@app.route('/unlike/<int:post_id>', methods=['POST'])
def unlike(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    # 「いいね」をデータベースから削除
    # 'likes' テーブルから、ログイン中のユーザーが指定された投稿に登録した「いいね」レコードを削除
    conn.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (session['user_id'], post_id))
    conn.commit() # データベースへの変更を確定
    conn.close()
    return redirect(request.referrer)

#DM送受信画面
@app.route('/message/<int:receiver_id>', methods=['GET', 'POST'])
def message(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # HTTPリクエストがPOSTメソッドの場合（メッセージが送信された時）
    if request.method == 'POST':
        # フォームからメッセージ内容を取得
        content = request.form['content']
        # 送信者（現在ログイン中のユーザー）のIDを取得
        
        sender_id = session['user_id']
        # メッセージをデータベースに挿入
        # 'messages' テーブルに、送信者ID、受信者ID、メッセージ内容を保存
        conn.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
                     (sender_id, receiver_id, content))
        conn.commit()# データベースへの変更を確定
        flash("メッセージを送信しました。")# 成功メッセージを表示

    # 送受信メッセージ取得
    # 送受信メッセージ取得
    # 現在ログインしているユーザー（user_id）と、DMの相手（receiver_id）との間の全てのメッセージを取得します。
    # sender_id が自分 AND receiver_id が相手、またはその逆のメッセージを、作成された順に並べて取得します。
    user_id = session['user_id']
    messages = conn.execute('''
        SELECT * FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at
    ''', (user_id, receiver_id, receiver_id, user_id)).fetchall()

     # DM相手のユーザー情報を取得
    # メッセージの相手のプロフィール情報（例: ユーザー名、表示名など）をデータベースから取得
    receiver = conn.execute("SELECT * FROM users WHERE user_id = ?", (receiver_id,)).fetchone()
    conn.close()

    # メッセージ画面のテンプレートをレンダリング
    # 取得したメッセージ履歴とDM相手の情報を 'message.html' テンプレートに渡して表示
    return render_template('message.html', messages=messages, receiver=receiver)


#DM受信画面
@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect('/login')

    # ログイン中のユーザーIDを取得
    user_id = session['user_id']
    conn = get_db_connection()
    c = conn.cursor()

    # DMのやり取りをした相手のユーザーID一覧を取得
    # 'messages' テーブルから、ログインユーザー（sender_id または receiver_id）が関わっている全てのメッセージを対象に、
    # 相手側の user_id を特定します。自分自身へのメッセージは除外します
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

    
    # 取得した相手のIDリストから重複を削除
    # 複数回メッセージをやり取りした場合でも、相手のIDが重複しないようにセット型に変換し、再度リストに戻す
    other_user_ids = [row['other_user_id'] for row in c.fetchall()]
    other_user_ids = list(set(other_user_ids))

    # 各相手のプロフィール情報を取得
    # 取得した相手のIDリストをループし、それぞれのユーザーのuser_id, username, display_nameを取得する
    conversations = []
    for other_id in other_user_ids:
        c.execute('SELECT user_id, username, display_name FROM users WHERE user_id = ?', (other_id,))
        user = c.fetchone()
        if user:
            conversations.append(user)

    conn.close()
     # 受信箱のテンプレートをレンダリング
    # 会話相手のリストを 'inbox.html' テンプレートに渡して表示
    return render_template('inbox.html', conversations=conversations)


#通知機能
@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # ログインユーザー宛の通知を取得
    # 'notifications' テーブルから、現在ログインしているユーザー宛ての通知を新しい順に取得
    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()

    # 通知を「既読」に更新
    # 取得した通知は全て読んだとみなし、'is_read' カラムを1（既読）に更新
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (session['user_id'],)
    )
    conn.commit()
    conn.close()

    # 通知画面のテンプレートをレンダリング
    # 取得した通知リストを 'notifications.html' テンプレートに渡して表示
    return render_template("notifications.html", notifications=notifs)



if __name__ == '__main__':
    app.run(debug=True)
