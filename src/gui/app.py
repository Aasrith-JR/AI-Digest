"""
Main Flask/Quart application for AI-Digest Web GUI.
Uses Quart for async support with Flask-like API.
"""
import os
import logging
from functools import wraps
from typing import Optional

from quart import Quart, render_template, request, redirect, url_for, flash, session, jsonify
from quart_cors import cors

from gui.models import UserDatabase
from gui.email_service import EmailService
from gui.config_service import (
    read_config_async, write_config_async, get_pipelines,
    get_email_colors, update_email_colors, read_config_sync
)
from core.personas import ALL_PERSONAS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = Quart(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app = cors(app)

# Secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'ai-digest-secret-key-change-in-production')

# Database path
DB_PATH = os.environ.get('GUI_DATABASE_PATH', 'data/gui.db')

# Initialize services
user_db: Optional[UserDatabase] = None
email_service: Optional[EmailService] = None


def get_user_db() -> UserDatabase:
    """Get or create UserDatabase instance."""
    global user_db
    if user_db is None:
        user_db = UserDatabase(DB_PATH)
    return user_db


def get_email_service() -> Optional[EmailService]:
    """Get or create EmailService instance."""
    global email_service
    if email_service is None:
        try:
            config = read_config_sync()
            smtp_host = config.get('EMAIL_SMTP_HOST')
            smtp_port = config.get('EMAIL_SMTP_PORT', 587)
            email_from = config.get('EMAIL_FROM')
            email_username = os.environ.get('EMAIL_USERNAME')
            email_password = os.environ.get('EMAIL_PASSWORD')

            if all([smtp_host, email_from, email_username, email_password]):
                email_service = EmailService(
                    smtp_host=smtp_host,
                    smtp_port=int(smtp_port),
                    username=email_username,
                    password=email_password,
                    sender=email_from
                )
        except Exception as e:
            logger.error(f"Failed to initialize email service: {e}")
    return email_service


# ==================== Decorators ====================

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return await f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return await f(*args, **kwargs)
    return decorated_function


# ==================== Startup ====================

@app.before_serving
async def startup():
    """Initialize database tables on startup."""
    db = get_user_db()
    await db.init_tables()
    logger.info("GUI application started, database initialized")


# ==================== Public Routes ====================

@app.route('/')
async def index():
    """Landing page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return await render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
async def login():
    """User login page."""
    if request.method == 'POST':
        form = await request.form
        email = form.get('email', '').strip().lower()
        password = form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return await render_template('login.html')

        db = get_user_db()
        user = await db.get_user_by_email(email)

        if not user:
            flash('Invalid email or password.', 'danger')
            return await render_template('login.html')

        if not db.verify_password(password, user['password_hash']):
            flash('Invalid email or password.', 'danger')
            return await render_template('login.html')

        if not user['is_verified']:
            flash('Please verify your email first.', 'warning')
            return redirect(url_for('verify_otp', email=email, purpose='registration'))

        if not user['is_active']:
            flash('Your account has been deactivated.', 'danger')
            return await render_template('login.html')

        # Create session
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['is_admin'] = bool(user['is_admin'])

        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))

    return await render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
async def register():
    """User registration page."""
    if request.method == 'POST':
        form = await request.form
        email = form.get('email', '').strip().lower()
        password = form.get('password', '')
        confirm_password = form.get('confirm_password', '')

        # Validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return await render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return await render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return await render_template('register.html')

        db = get_user_db()

        # Check if user already exists
        existing_user = await db.get_user_by_email(email)
        if existing_user:
            if existing_user['is_verified']:
                flash('An account with this email already exists.', 'danger')
                return await render_template('register.html')
            else:
                # User exists but not verified, resend OTP
                pass
        else:
            # Create new user
            user_id = await db.create_user(email, password)
            if not user_id:
                flash('Failed to create account. Please try again.', 'danger')
                return await render_template('register.html')

        # Generate and send OTP
        otp = await db.create_otp(email, 'registration')

        es = get_email_service()
        if es:
            sent = await es.send_otp_email(email, otp, 'registration')
            if not sent:
                flash('Failed to send verification email. Please try again.', 'danger')
                return await render_template('register.html')
        else:
            # For development without email service
            logger.warning(f"Email service not configured. OTP for {email}: {otp}")
            flash(f'Email service not configured. Your OTP is: {otp}', 'info')

        flash('Registration initiated! Check your email for the verification code.', 'success')
        return redirect(url_for('verify_otp', email=email, purpose='registration'))

    return await render_template('register.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
async def verify_otp():
    """OTP verification page."""
    email = request.args.get('email', '')
    purpose = request.args.get('purpose', 'registration')

    if request.method == 'POST':
        form = await request.form
        email = form.get('email', '').strip().lower()
        otp = form.get('otp', '').strip()
        purpose = form.get('purpose', 'registration')

        if not email or not otp:
            flash('Email and OTP are required.', 'danger')
            return await render_template('verify_otp.html', email=email, purpose=purpose)

        db = get_user_db()

        # Verify OTP
        if await db.verify_otp(email, otp, purpose):
            if purpose == 'registration':
                # Mark user as verified
                await db.verify_user(email)

                # Send welcome email
                es = get_email_service()
                if es:
                    await es.send_welcome_email(email)

                flash('Account verified successfully! You can now log in.', 'success')
                return redirect(url_for('login'))
            elif purpose == 'password_reset':
                # Store email in session for password reset
                session['reset_email'] = email
                return redirect(url_for('reset_password'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')

    return await render_template('verify_otp.html', email=email, purpose=purpose)


@app.route('/resend-otp', methods=['POST'])
async def resend_otp():
    """Resend OTP code."""
    form = await request.form
    email = form.get('email', '').strip().lower()
    purpose = form.get('purpose', 'registration')

    if not email:
        flash('Email is required.', 'danger')
        return redirect(url_for('register'))

    db = get_user_db()
    otp = await db.create_otp(email, purpose)

    es = get_email_service()
    if es:
        sent = await es.send_otp_email(email, otp, purpose)
        if sent:
            flash('A new verification code has been sent to your email.', 'success')
        else:
            flash('Failed to send verification email. Please try again.', 'danger')
    else:
        logger.warning(f"Email service not configured. OTP for {email}: {otp}")
        flash(f'Email service not configured. Your OTP is: {otp}', 'info')

    return redirect(url_for('verify_otp', email=email, purpose=purpose))


@app.route('/forgot-password', methods=['GET', 'POST'])
async def forgot_password():
    """Forgot password page."""
    if request.method == 'POST':
        form = await request.form
        email = form.get('email', '').strip().lower()

        if not email:
            flash('Email is required.', 'danger')
            return await render_template('forgot_password.html')

        db = get_user_db()
        user = await db.get_user_by_email(email)

        if user:
            # Generate and send OTP
            otp = await db.create_otp(email, 'password_reset')

            es = get_email_service()
            if es:
                await es.send_otp_email(email, otp, 'password_reset')
            else:
                logger.warning(f"Email service not configured. OTP for {email}: {otp}")
                flash(f'Email service not configured. Your OTP is: {otp}', 'info')

        # Always show success to prevent email enumeration
        flash('If an account exists with this email, a password reset code has been sent.', 'info')
        return redirect(url_for('verify_otp', email=email, purpose='password_reset'))

    return await render_template('forgot_password.html')


@app.route('/reset-password', methods=['GET', 'POST'])
async def reset_password():
    """Reset password page."""
    if 'reset_email' not in session:
        flash('Invalid password reset session.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        form = await request.form
        password = form.get('password', '')
        confirm_password = form.get('confirm_password', '')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return await render_template('reset_password.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return await render_template('reset_password.html')

        db = get_user_db()
        email = session.pop('reset_email')

        if await db.update_password(email, password):
            flash('Password reset successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Failed to reset password. Please try again.', 'danger')

    return await render_template('reset_password.html')


@app.route('/logout')
async def logout():
    """User logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ==================== User Dashboard Routes ====================

@app.route('/dashboard')
@login_required
async def dashboard():
    """User dashboard."""
    db = get_user_db()
    user = await db.get_user_by_id(session['user_id'])
    user_personas = await db.get_user_personas(session['user_id'])

    # Get available personas from config
    pipelines = await get_pipelines()
    available_personas = list(pipelines.keys())

    # Create a dict of subscribed personas
    subscribed = {p['persona_name']: p['is_subscribed'] for p in user_personas}

    return await render_template('dashboard.html',
                                  user=user,
                                  available_personas=available_personas,
                                  subscribed=subscribed,
                                  ALL_PERSONAS=ALL_PERSONAS)


@app.route('/personas', methods=['GET', 'POST'])
@login_required
async def manage_personas():
    """Manage persona subscriptions."""
    db = get_user_db()

    if request.method == 'POST':
        form = await request.form
        selected_personas = form.getlist('personas')

        await db.update_user_personas(session['user_id'], selected_personas)
        flash('Persona subscriptions updated!', 'success')
        return redirect(url_for('dashboard'))

    # Get available personas from config
    pipelines = await get_pipelines()
    available_personas = list(pipelines.keys())

    user_personas = await db.get_user_personas(session['user_id'])
    subscribed = {p['persona_name']: p['is_subscribed'] for p in user_personas}

    return await render_template('personas.html',
                                  available_personas=available_personas,
                                  subscribed=subscribed,
                                  pipelines=pipelines,
                                  ALL_PERSONAS=ALL_PERSONAS)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
async def profile():
    """User profile page."""
    db = get_user_db()

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')

        if action == 'change_password':
            current_password = form.get('current_password', '')
            new_password = form.get('new_password', '')
            confirm_password = form.get('confirm_password', '')

            user = await db.get_user_by_id(session['user_id'])

            if not db.verify_password(current_password, user['password_hash']):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            elif len(new_password) < 8:
                flash('Password must be at least 8 characters.', 'danger')
            else:
                await db.update_password(user['email'], new_password)
                flash('Password updated successfully!', 'success')

    user = await db.get_user_by_id(session['user_id'])
    return await render_template('profile.html', user=user)


# ==================== Admin Routes ====================

@app.route('/admin')
@admin_required
async def admin_dashboard():
    """Admin dashboard."""
    db = get_user_db()
    users = await db.get_all_users()
    pipelines = await get_pipelines()
    config = await read_config_async()

    return await render_template('admin/dashboard.html',
                                  users=users,
                                  pipelines=pipelines,
                                  config=config)


@app.route('/admin/users')
@admin_required
async def admin_users():
    """User management page."""
    db = get_user_db()
    users = await db.get_all_users()
    return await render_template('admin/users.html', users=users)


@app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
async def toggle_user_admin(user_id: int):
    """Toggle user's admin status."""
    # Prevent an admin from toggling their own admin status
    if 'user_id' in session and user_id == session['user_id']:
        flash("You cannot change your own admin status.", 'warning')
        return redirect(url_for('admin_users'))

    db = get_user_db()
    user = await db.get_user_by_id(user_id)

    if user:
        new_status = not user['is_admin']
        await db.set_admin(user['email'], new_status)
        flash(f"Admin status updated for {user['email']}.", 'success')
    else:
        flash('User not found.', 'danger')

    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
async def delete_user(user_id: int):
    """Delete a user."""
    if user_id == session['user_id']:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin_users'))

    db = get_user_db()
    if await db.delete_user(user_id):
        flash('User deleted successfully.', 'success')
    else:
        flash('Failed to delete user.', 'danger')

    return redirect(url_for('admin_users'))


@app.route('/admin/config', methods=['GET', 'POST'])
@admin_required
async def admin_config():
    """Configuration editor page."""
    if request.method == 'POST':
        form = await request.form
        action = form.get('action')

        if action == 'update_email_settings':
            config = await read_config_async()
            config['EMAIL_ENABLED'] = form.get('email_enabled') == 'true'
            config['EMAIL_SMTP_HOST'] = form.get('smtp_host', '')
            config['EMAIL_SMTP_PORT'] = int(form.get('smtp_port', 587))
            config['EMAIL_FROM'] = form.get('email_from', '')

            if await write_config_async(config):
                flash('Email settings updated!', 'success')
            else:
                flash('Failed to update email settings.', 'danger')

        elif action == 'update_colors':
            colors = {
                'primary': form.get('color_primary', '#00F6FF'),
                'primary_dark': form.get('color_primary_dark', '#0047FF'),
                'secondary': form.get('color_secondary', '#B896FF'),
                'background': form.get('color_background', '#060606'),
                'card_bg': form.get('color_card_bg', '#060606'),
                'text_primary': form.get('color_text_primary', '#FBFAFA'),
                'text_secondary': form.get('color_text_secondary', '#7BA8FF'),
                'border': form.get('color_border', '#0047FF'),
                'accent': form.get('color_accent', '#00FFF0'),
                'why_it_matters_bg': form.get('color_why_it_matters_bg', '#060606'),
                'why_it_matters_text': form.get('color_why_it_matters_text', '#00FFF0'),
            }

            if await update_email_colors(colors):
                flash('Email colors updated!', 'success')
            else:
                flash('Failed to update email colors.', 'danger')

        return redirect(url_for('admin_config'))

    config = await read_config_async()
    email_colors = await get_email_colors()

    return await render_template('admin/config.html',
                                  config=config,
                                  email_colors=email_colors)


@app.route('/admin/pipelines', methods=['GET'])
@admin_required
async def admin_pipelines():
    """Pipeline management page."""
    config = await read_config_async()
    pipelines = config.get('pipelines', {})
    return await render_template('admin/pipelines.html', pipelines=pipelines)


@app.route('/admin/pipelines/<name>/toggle', methods=['POST'])
@admin_required
async def toggle_pipeline(name: str):
    """Toggle pipeline enabled status."""
    config = await read_config_async()

    if 'pipelines' in config and name in config['pipelines']:
        config['pipelines'][name]['enabled'] = not config['pipelines'][name].get('enabled', True)

        if await write_config_async(config):
            status = "enabled" if config['pipelines'][name]['enabled'] else "disabled"
            flash(f'Pipeline "{name}" {status}.', 'success')
        else:
            flash('Failed to update pipeline.', 'danger')

    return redirect(url_for('admin_pipelines'))


@app.route('/admin/pipelines/<name>/edit', methods=['GET', 'POST'])
@admin_required
async def edit_pipeline(name: str):
    """Edit pipeline configuration."""
    config = await read_config_async()

    if name not in config.get('pipelines', {}):
        flash('Pipeline not found.', 'danger')
        return redirect(url_for('admin_pipelines'))

    if request.method == 'POST':
        form = await request.form

        pipeline = config['pipelines'][name]
        pipeline['enabled'] = form.get('enabled') == 'true'
        pipeline['persona'] = form.get('persona', pipeline.get('persona', 'GENAI_NEWS'))
        pipeline['fetch_hours'] = int(form.get('fetch_hours', pipeline.get('fetch_hours', 24)))
        pipeline['default_audience'] = form.get('default_audience', pipeline.get('default_audience', 'developer'))
        pipeline['score_field'] = form.get('score_field', pipeline.get('score_field', 'relevance_score'))
        pipeline['why_it_matters_field'] = form.get('why_it_matters_field', pipeline.get('why_it_matters_field', 'why_it_matters'))
        pipeline['why_it_matters_fallback'] = form.get('why_it_matters_fallback', pipeline.get('why_it_matters_fallback', ''))

        # Update ingestion settings
        if 'ingestion' not in pipeline:
            pipeline['ingestion'] = {}
        pipeline['ingestion']['top_k'] = int(form.get('top_k', pipeline['ingestion'].get('top_k', 5)))
        pipeline['ingestion']['min_engagement'] = int(form.get('min_engagement', pipeline['ingestion'].get('min_engagement', 5)))
        pipeline['ingestion']['keywords'] = [
            k.strip() for k in form.get('keywords', ','.join(pipeline['ingestion'].get('keywords', []))).split(',') if k.strip()
        ]

        # Parse sources JSON safely
        sources_raw = form.get('sources_json', '').strip()
        if sources_raw:
            import json
            try:
                sources_parsed = json.loads(sources_raw)
                if isinstance(sources_parsed, list):
                    # Basic normalization: ensure dict items and default enabled true
                    normalized = []
                    for s in sources_parsed:
                        if isinstance(s, dict) and 'type' in s:
                            item = dict(s)
                            if 'enabled' not in item:
                                item['enabled'] = True
                            normalized.append(item)
                    pipeline['ingestion']['sources'] = normalized
                else:
                    flash('Sources must be a JSON array.', 'danger')
                    return await render_template('admin/edit_pipeline.html', name=name, pipeline=pipeline, ALL_PERSONAS=ALL_PERSONAS)
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON for sources: {e}', 'danger')
                return await render_template('admin/edit_pipeline.html', name=name, pipeline=pipeline, ALL_PERSONAS=ALL_PERSONAS)

        if await write_config_async(config):
            flash('Pipeline updated successfully!', 'success')
            return redirect(url_for('admin_pipelines'))
        else:
            flash('Failed to update pipeline.', 'danger')

    pipeline = config['pipelines'][name]
    return await render_template('admin/edit_pipeline.html',
                                  name=name,
                                  pipeline=pipeline,
                                  ALL_PERSONAS=ALL_PERSONAS)



# ==================== API Endpoints ====================

@app.route('/api/personas')
@login_required
async def api_get_personas():
    """Get available personas."""
    pipelines = await get_pipelines()
    return jsonify({
        'personas': list(pipelines.keys()),
        'details': {name: {'enabled': p.get('enabled', True)} for name, p in pipelines.items()}
    })


@app.route('/api/user/personas', methods=['GET', 'POST'])
@login_required
async def api_user_personas():
    """Get or update user persona subscriptions."""
    db = get_user_db()

    if request.method == 'POST':
        data = await request.get_json()
        personas = data.get('personas', [])
        await db.update_user_personas(session['user_id'], personas)
        return jsonify({'status': 'success'})

    user_personas = await db.get_user_personas(session['user_id'])
    return jsonify({
        'subscriptions': [p['persona_name'] for p in user_personas if p['is_subscribed']]
    })


@app.route('/api/config', methods=['GET'])
@admin_required
async def api_get_config():
    """Get current configuration (admin only)."""
    config = await read_config_async()
    # Remove sensitive data
    config.pop('EMAIL_PASSWORD', None)
    return jsonify(config)


@app.route('/api/subscribers/<persona>')
@admin_required
async def api_get_subscribers(persona: str):
    """Get subscribers for a persona (admin only)."""
    db = get_user_db()
    users = await db.get_verified_users_with_persona(persona)
    return jsonify({'subscribers': [u['email'] for u in users]})


@app.route('/api/run-digest', methods=['POST'])
@admin_required
async def api_run_digest():
    """Run a digest pipeline (admin only)."""
    try:
        from gui.tasks import task_runner, run_digest_async

        data = await request.get_json() or {}
        persona = data.get('persona')

        # Start the task in background
        task_id = await task_runner.run_async(run_digest_async, persona)

        return jsonify({
            'status': 'started',
            'task_id': task_id,
            'message': f'Digest run started for {"all pipelines" if not persona else persona}'
        })
    except Exception as e:
        logger.error(f"Failed to start digest run: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/task/<task_id>')
@admin_required
async def api_task_status(task_id: str):
    """Get task status (admin only)."""
    from gui.tasks import task_runner

    if task_runner.is_running(task_id):
        return jsonify({'status': 'running', 'task_id': task_id})

    result = task_runner.get_result(task_id)
    if result:
        return jsonify({
            'status': 'completed' if result.success else 'failed',
            'task_id': task_id,
            'success': result.success,
            'result': result.result,
            'error': result.error,
            'duration': result.duration
        })

    return jsonify({'status': 'not_found', 'task_id': task_id}), 404


# ==================== Admin Tools ====================

@app.route('/admin/run-digest', methods=['GET', 'POST'])
@admin_required
async def admin_run_digest():
    """Admin page to run digest manually."""
    pipelines = await get_pipelines()

    if request.method == 'POST':
        form = await request.form
        persona = form.get('persona', '')

        try:
            from gui.tasks import task_runner, run_digest_async

            task_id = await task_runner.run_async(
                run_digest_async,
                persona if persona else None
            )

            flash(f'Digest run started! Task ID: {task_id}', 'success')
        except Exception as e:
            flash(f'Failed to start digest: {e}', 'danger')

        return redirect(url_for('admin_run_digest'))

    return await render_template('admin/run_digest.html', pipelines=pipelines)


# ==================== Error Handlers ====================

@app.errorhandler(404)
async def not_found(error):
    return await render_template('errors/404.html'), 404


@app.errorhandler(500)
async def server_error(error):
    return await render_template('errors/500.html'), 500


# ==================== Run Application ====================

def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the Quart application."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app(debug=True)
