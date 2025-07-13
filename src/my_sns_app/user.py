import os
import uuid
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, jsonify
)
from my_sns_app.db import get_db
from my_sns_app.auth import login_required
from my_sns_app.utils import allowed_file

bp = Blueprint('user', __name__)

@bp.route('/profile')
@login_required
def profile():
    db = get_db()
    
    # 自分のフォロー数・フォロワー数を取得
    followers_count = db.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (g.user['user_id'],)).fetchone()[0]
    following_count = db.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (g.user['user_id'],)).fetchone()[0]
    
    # 最近の通知5件を取得
    notifications = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (g.user['user_id'],)
    ).fetchall()

    return render_template('profile.html', user=g.user, followers=followers_count, following=following_count, notifications=notifications)

@bp.route('/user/<int:user_id>')
def user_profile(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        return "ユーザーが見つかりませんでした", 404
    
    # 表示するユーザーのフォロー数・フォロワー数を取得
    followers_count = db.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,)).fetchone()[0]
    following_count = db.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,)).fetchone()[0]

    is_self = g.user and g.user['user_id'] == user_id
    is_following = False
    if g.user and not is_self:
        is_following = db.execute(
            'SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?',
            (g.user['user_id'], user_id)
        ).fetchone() is not None
        
    return render_template('user_profile.html', user=user, followers=followers_count, following=following_count, is_self=is_self, is_following=is_following)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        display_name = request.form['display_name']
        username = request.form['username']
        bio = request.form['bio']
        db = get_db()
        
        db.execute(
            "UPDATE users SET display_name = ?, username = ?, bio = ? WHERE user_id = ?",
            (display_name, username, bio, g.user['user_id'])
        )

        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4()}.{ext}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                db.execute(
                    "UPDATE users SET profile_image = ? WHERE user_id = ?",
                    (filename, g.user['user_id'])
                )
        
        db.commit()
        flash("プロフィールを更新しました。")
        return redirect(url_for('user.profile'))

    return render_template('edit_profile.html', user=g.user)

@bp.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    if g.user['user_id'] == user_id:
        return jsonify({'status': 'error', 'message': '自分自身はフォローできません。'}), 400
    
    db = get_db()
    db.execute("INSERT OR IGNORE INTO follows (follower_id, followed_id) VALUES (?, ?)", (g.user['user_id'], user_id))
    db.commit()
    
    followers_count = db.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,)).fetchone()[0]
    return jsonify({'status': 'success', 'following': True, 'followers_count': followers_count})

@bp.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    db = get_db()
    db.execute("DELETE FROM follows WHERE follower_id = ? AND followed_id = ?", (g.user['user_id'], user_id))
    db.commit()

    followers_count = db.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,)).fetchone()[0]
    return jsonify({'status': 'success', 'following': False, 'followers_count': followers_count})

@bp.route('/user/<int:user_id>/following')
def following(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    if not user:
        return "ユーザーが見つかりません。", 404

    user_list = db.execute('''
        SELECT u.user_id, u.username, u.display_name, u.profile_image
        FROM users u JOIN follows f ON u.user_id = f.followed_id
        WHERE f.follower_id = ?
    ''', (user_id,)).fetchall()
    
    return render_template('user_list.html', user=user, user_list=user_list, list_type='following')

@bp.route('/user/<int:user_id>/followers')
def followers(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    if not user:
        return "ユーザーが見つかりません。", 404

    user_list = db.execute('''
        SELECT u.user_id, u.username, u.display_name, u.profile_image
        FROM users u JOIN follows f ON u.user_id = f.follower_id
        WHERE f.followed_id = ?
    ''', (user_id,)).fetchall()
    
    return render_template('user_list.html', user=user, user_list=user_list, list_type='followers')