# src/my_sns_app/post.py

import os
import uuid
import re
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, jsonify
)
from my_sns_app.db import get_db
from my_sns_app.auth import login_required
from my_sns_app.utils import allowed_file

bp = Blueprint('post', __name__)

# (create_post関数は変更なし)
@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form['content']
        image = None
        
        if not content:
            flash("投稿内容がありません。")
            return redirect(url_for('post.create_post'))

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4()}.{ext}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                image = filename
        
        db = get_db()
        cursor = db.execute(
            "INSERT INTO posts (user_id, content, image) VALUES (?, ?, ?)",
            (g.user['user_id'], content, image)
        )
        post_id = cursor.lastrowid

        hashtags = re.findall(r'#(\w+)', content)
        for tag_name in set(hashtags):
            tag = db.execute('SELECT id FROM hashtags WHERE name = ?', (tag_name,)).fetchone()
            if tag is None:
                tag_cursor = db.execute('INSERT INTO hashtags (name) VALUES (?)', (tag_name,))
                tag_id = tag_cursor.lastrowid
            else:
                tag_id = tag['id']
            db.execute(
                'INSERT OR IGNORE INTO post_hashtags (post_id, hashtag_id) VALUES (?, ?)',
                (post_id, tag_id)
            )
        
        db.commit()
        flash("投稿しました。")
        return redirect(url_for('main.timeline'))
    
    return render_template('create_post.html')


# --- ▼▼▼ ここから修正 ▼▼▼ ---

@bp.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO likes (user_id, post_id) VALUES (?, ?)", (g.user['user_id'], post_id))
    db.commit()
    
    like_count = db.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,)).fetchone()[0]
    
    return jsonify({'status': 'success', 'liked': True, 'count': like_count})

@bp.route('/unlike/<int:post_id>', methods=['POST'])
@login_required
def unlike(post_id):
    db = get_db()
    db.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (g.user['user_id'], post_id))
    db.commit()
    
    like_count = db.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,)).fetchone()[0]

    return jsonify({'status': 'success', 'liked': False, 'count': like_count})

# --- ▲▲▲ ここまで修正 ▲▲▲ ---

@bp.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    content = request.form['comment']
    if not content:
        flash('コメントが空です。')
        return redirect(request.referrer or url_for('main.timeline'))

    db = get_db()
    db.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (post_id, g.user['user_id'], content)
    )

    post_author = db.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post_author and post_author['user_id'] != g.user['user_id']:
        message = f"{g.user['username']}さんがあなたの投稿にコメントしました。"
        db.execute(
            "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
            (post_author['user_id'], message)
        )

    db.commit()
    return redirect(request.referrer or url_for('main.timeline'))