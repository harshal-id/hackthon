from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from datetime import datetime
from models import db, Pass, Room, Complaint, User

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key'

# ─────────────────────────────────────────
import os
# 🔧 CONFIG
# ─────────────────────────────────────────
database_url = os.environ.get('DATABASE_URL', 'postgresql://hackthon_wc12_user:6GlcoFNOB94dLvYUpeUwQwJfFUf9JiP2@dpg-d715jbq4d50c73bf24r0-a.oregon-postgres.render.com/hackthon_wc12')
# Render provides 'postgres://' but SQLAlchemy 1.4+ requires 'postgresql://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ─────────────────────────────────────────
# 🟢 CREATE DATABASE
# ─────────────────────────────────────────
with app.app_context():
    db.create_all()
    try:
        db.session.execute(text("ALTER TABLE complaint ADD COLUMN author VARCHAR(100)"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    
    if not User.query.first():
        w = User(username='warden', password_hash=generate_password_hash('warden'), role='warden')
        s = User(username='student', password_hash=generate_password_hash('student'), role='student')
        db.session.add_all([w, s])
        db.session.commit()



# ─────────────────────────────────────────
# 🔑 AUTHENTICATION
# ─────────────────────────────────────────
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))
            
        flash('Invalid username or password')
        return redirect(url_for('login'))
        
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# 🏠 DASHBOARD

# ─────────────────────────────────────────
@app.route("/")
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    passes = Pass.query.all() if session.get('role') == 'warden' else Pass.query.filter_by(name=session.get('username')).all() if session.get('role') == 'warden' else Pass.query.filter_by(name=session.get('username')).all()
    complaints = Complaint.query.all() if session.get('role') == 'warden' else Complaint.query.filter_by(author=session.get('username')).all() if session.get('role') == 'warden' else Complaint.query.filter_by(author=session.get('username')).all()
    rooms = Room.query.all()

    stats = {
        "total_students": len(rooms),
        "pending_passes": Pass.query.filter_by(status="pending").count(),
        "vacant_rooms": Room.query.filter_by(status="vacant").count(),
        "sla_breaches": Complaint.query.filter_by(status="breach").count()
    }

    activities = [
        {"title": "System", "desc": "Dashboard loaded", "time": "now", "color": "green"}
    ]

    current_date = datetime.now().strftime("%A, %d %B %Y")

    return render_template(
        "home.html",
        stats=stats,
        activities=activities,
        passes=passes,
        current_date=current_date
    )
@app.route('/api/chart/passes')
def chart_passes():
    from collections import Counter

    passes = Pass.query.all() if session.get('role') == 'warden' else Pass.query.filter_by(name=session.get('username')).all()

    # Example: count by status
    counts = Counter([p.status for p in passes])

    return jsonify({
        "labels": list(counts.keys()),
        "values": list(counts.values())
    })
# ─────────────────────────────────────────
# 🟢 API: GET DATA
# ─────────────────────────────────────────

@app.route('/api/passes')
def get_passes():
    passes = Pass.query.all() if session.get('role') == 'warden' else Pass.query.filter_by(name=session.get('username')).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "room": p.room,
            "status": p.status
        } for p in passes
    ])


@app.route('/api/rooms')
def get_rooms():
    rooms = Room.query.all()
    return jsonify([
        {
            "num": r.num,
            "status": r.status,
            "student": r.student
        } for r in rooms
    ])


@app.route('/api/complaints')
def get_complaints():
    complaints = Complaint.query.all() if session.get('role') == 'warden' else Complaint.query.filter_by(author=session.get('username')).all()
    return jsonify([
        {
            "id": c.id,
            "title": c.title,
            "status": c.status
        } for c in complaints
    ])

# ─────────────────────────────────────────
# 🟢 API: UPDATE ACTIONS
# ─────────────────────────────────────────

@app.route('/api/approve/<int:id>', methods=['POST'])
def approve_pass(id):
    if session.get('role') != 'warden': return jsonify({'success': False}), 403
    p = Pass.query.get(id)
    if not p:
        return jsonify({"success": False, "error": "Pass not found"}), 404

    p.status = "approved"
    db.session.commit()

    return jsonify({"success": True})


@app.route('/api/reject/<int:id>', methods=['POST'])
def reject_pass(id):
    if session.get('role') != 'warden': return jsonify({'success': False}), 403
    p = Pass.query.get(id)
    if not p:
        return jsonify({"success": False, "error": "Pass not found"}), 404

    p.status = "rejected"
    db.session.commit()

    return jsonify({"success": True})

# ─────────────────────────────────────────
# 🟢 API: CREATE DATA
# ─────────────────────────────────────────

@app.route('/api/add_pass', methods=['POST'])
def add_pass():
    data = request.json

    new_pass = Pass(
        name=session.get("username", data.get("name")),
        room=data.get("room"),
        status="pending"
    )

    db.session.add(new_pass)
    db.session.commit()

    return jsonify({"success": True})


@app.route('/api/add_room', methods=['POST'])
def add_room():
    data = request.json

    room = Room(
        num=data.get("num"),
        status=data.get("status"),
        student=data.get("student")
    )

    db.session.add(room)
    db.session.commit()

    return jsonify({"success": True})


@app.route('/api/add_complaint', methods=['POST'])
def add_complaint():
    data = request.json

    complaint = Complaint(
        title=data.get("title"),
        status="warning",
        author=session.get("username")
    )

    db.session.add(complaint)
    db.session.commit()

    return jsonify({"success": True})

# ─────────────────────────────────────────
# 🟢 OPTIONAL: DELETE (GOOD PRACTICE)
# ─────────────────────────────────────────

@app.route('/api/delete_pass/<int:id>', methods=['DELETE'])
def delete_pass(id):
    p = Pass.query.get(id)
    if not p:
        return jsonify({"success": False}), 404

    db.session.delete(p)
    db.session.commit()

    return jsonify({"success": True})

# ─────────────────────────────────────────
# 🚀 RUN
# ─────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)