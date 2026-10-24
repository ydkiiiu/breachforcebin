from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Database URL handling (works with both SQLite and Postgres from Railway/Render)
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/pastebin.db')
if database_url.startswith('postgres://'):
    # Railway/Render sometimes give postgres:// which SQLAlchemy doesn't like
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


# ==================== MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pastes = db.relationship('Paste', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Paste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paste_id = db.Column(db.String(12), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), default='Untitled')
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), default='text')
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    views = db.Column(db.Integer, default=0)

    def is_expired(self):
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== HELPERS ====================

def generate_paste_id():
    return secrets.token_urlsafe(8)[:10]


def create_admin_if_not_exists():
    """Create a default admin account if none exists."""
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')  # Change this after first login!
        db.session.add(admin)
        db.session.commit()
        print("Default admin created → username: admin / password: admin123")


# ==================== ROUTES ====================

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pastes = Paste.query.filter_by(is_public=True)\
                        .order_by(Paste.created_at.desc())\
                        .paginate(page=page, per_page=20, error_out=False)
    return render_template('index.html', pastes=pastes)


@app.route('/paste', methods=['GET', 'POST'])
def create_paste():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        title = request.form.get('title', 'Untitled').strip() or 'Untitled'
        language = request.form.get('language', 'text')
        expiration = request.form.get('expiration', 'never')
        is_public = request.form.get('is_public') == 'on'

        if not content:
            flash('Paste content cannot be empty.', 'error')
            return redirect(url_for('create_paste'))

        expires_at = None
        if expiration == '1h':
            expires_at = datetime.utcnow() + timedelta(hours=1)
        elif expiration == '1d':
            expires_at = datetime.utcnow() + timedelta(days=1)
        elif expiration == '1w':
            expires_at = datetime.utcnow() + timedelta(weeks=1)
        elif expiration == '1m':
            expires_at = datetime.utcnow() + timedelta(days=30)

        paste = Paste(
            paste_id=generate_paste_id(),
            title=title,
            content=content,
            language=language,
            is_public=is_public,
            expires_at=expires_at,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(paste)
        db.session.commit()
        return redirect(url_for('view_paste', paste_id=paste.paste_id))

    return render_template('create.html')


@app.route('/p/<paste_id>')
def view_paste(paste_id):
    paste = Paste.query.filter_by(paste_id=paste_id).first_or_404()
    if paste.is_expired():
        db.session.delete(paste)
        db.session.commit()
        abort(404)
    paste.views += 1
    db.session.commit()
    return render_template('view.html', paste=paste)


@app.route('/users')
def users():
    # Public user list (basic info only)
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users_list)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('register'))

        if len(username) < 3 or len(username) > 30:
            flash('Username must be between 3 and 30 characters.', 'error')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now sign in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ==================== ADMIN PANEL (hidden) ====================

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        abort(404)  # Hide existence from non-admins

    users = User.query.order_by(User.created_at.desc()).all()
    pastes = Paste.query.order_by(Paste.created_at.desc()).limit(50).all()
    return render_template('admin.html', users=users, pastes=pastes)


@app.route('/admin/create-user', methods=['POST'])
@login_required
def admin_create_user():
    if not current_user.is_admin:
        abort(404)

    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == 'on'

    if not username or not password:
        flash('Username and password required.', 'error')
        return redirect(url_for('admin_panel'))

    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('admin_panel'))

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f'User "{username}" created successfully.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        abort(404)

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete yourself.', 'error')
        return redirect(url_for('admin_panel'))

    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" deleted.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete-paste/<int:paste_id>', methods=['POST'])
@login_required
def admin_delete_paste(paste_id):
    if not current_user.is_admin:
        abort(404)

    paste = Paste.query.get_or_404(paste_id)
    db.session.delete(paste)
    db.session.commit()
    flash('Paste deleted.', 'success')
    return redirect(url_for('admin_panel'))


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# ==================== INIT ====================

def init_db():
    """Initialize database tables and default admin. Safe to call multiple times."""
    try:
        with app.app_context():
            db.create_all()
            create_admin_if_not_exists()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Database init warning: {e}")


# Run init when the app starts (works better with Gunicorn)
init_db()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
