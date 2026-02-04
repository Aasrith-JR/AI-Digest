# AI-Digest Web GUI

A web-based frontend for managing AI-Digest users, personas, and configurations.

## Features

- **User Authentication**: Email-based registration with OTP verification
- **Persona Management**: Subscribe to different digest personas
- **Admin Dashboard**: Manage users, pipelines, and configurations
- **Multi-user Email Delivery**: Send digests to all registered users
- **Async Architecture**: Built with Quart (async Flask) for high performance

## Quick Start

### 1. Initialize the Database

```bash
cd src
python -m gui.run_gui init-db
```

### 2. Create an Admin User

```bash
python -m gui.run_gui create-admin
```

Follow the prompts to enter email and password.

### 3. Start the Web Server

```bash
python -m gui.run_gui run --port 5000
```

For development with auto-reload:
```bash
python -m gui.run_gui run --port 5000 --debug
```

### 4. Access the Application

Open http://localhost:5000 in your browser.

## Configuration

### Environment Variables

Create or update your `.env` file:

```env
# GUI Settings
FLASK_SECRET_KEY=your-secret-key-here
GUI_DATABASE_PATH=data/gui.db

# Email Settings (for OTP and notifications)
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Email Service

The GUI uses the same SMTP settings from `resources/config.yml`:

```yaml
EMAIL_ENABLED: true
EMAIL_SMTP_HOST: smtp.gmail.com
EMAIL_SMTP_PORT: 587
EMAIL_FROM: your-email@gmail.com
```

## User Workflow

1. **Register**: User enters email and password
2. **Verify OTP**: User receives a 6-digit code via email
3. **Login**: After verification, user can log in
4. **Subscribe to Personas**: User selects which digest types to receive
5. **Receive Digests**: When digests run, emails are sent to all subscribed users

## Admin Features

Admins can:
- View and manage all users
- Toggle user admin status
- Delete users
- View and edit pipelines
- Configure email settings and colors
- Manually run digest pipelines

## Architecture

```
src/gui/
├── __init__.py          # Package init
├── app.py               # Main Quart application
├── models.py            # Database models (UserDatabase)
├── email_service.py     # Email sending service
├── config_service.py    # Config file management
├── multi_user_delivery.py # Multi-user email delivery
├── tasks.py             # Background task runner
├── run_gui.py           # CLI entry point
├── static/              # Static assets
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
└── templates/           # Jinja2 templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── verify_otp.html
    ├── dashboard.html
    ├── personas.html
    ├── profile.html
    ├── admin/
    │   ├── dashboard.html
    │   ├── users.html
    │   ├── pipelines.html
    │   ├── config.html
    │   ├── edit_pipeline.html
    │   └── run_digest.html
    └── errors/
        ├── 404.html
        └── 500.html
```

## API Endpoints

### Public
- `GET /` - Landing page
- `POST /login` - User login
- `POST /register` - User registration
- `POST /verify-otp` - OTP verification
- `POST /resend-otp` - Resend OTP
- `POST /forgot-password` - Password reset request
- `POST /reset-password` - Reset password

### Authenticated Users
- `GET /dashboard` - User dashboard
- `GET/POST /personas` - Manage subscriptions
- `GET/POST /profile` - User profile

### Admin Only
- `GET /admin` - Admin dashboard
- `GET /admin/users` - User management
- `POST /admin/users/<id>/toggle-admin` - Toggle admin status
- `POST /admin/users/<id>/delete` - Delete user
- `GET/POST /admin/config` - Configuration settings
- `GET /admin/pipelines` - Pipeline management
- `POST /admin/pipelines/<name>/toggle` - Toggle pipeline
- `GET/POST /admin/pipelines/<name>/edit` - Edit pipeline
- `GET/POST /admin/run-digest` - Run digest manually

### API
- `GET /api/personas` - List personas
- `GET/POST /api/user/personas` - User subscriptions
- `GET /api/config` - Get config (admin)
- `GET /api/subscribers/<persona>` - Get subscribers (admin)
- `POST /api/run-digest` - Run digest (admin)
- `GET /api/task/<id>` - Check task status (admin)

## Production Deployment

For production, use Hypercorn:

```bash
pip install hypercorn
hypercorn gui.app:app --bind 0.0.0.0:5000
```

Or with the run script:
```bash
python -m gui.run_gui run --host 0.0.0.0 --port 5000
```

## Security Notes

1. Change `FLASK_SECRET_KEY` to a strong random value
2. Use HTTPS in production
3. Store credentials in `.env`, not in config files
4. Regularly clean up expired sessions and OTPs
