# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
import os

load_dotenv()  # Load environment variables from .env file

# Global extensions
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")  # Add this line
limiter = Limiter(key_func=get_remote_address)  # make global instance

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'),
         static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
    )

    
    @app.context_processor
    def inject_user():
        from flask import session
        from app.models import User
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        return dict(user=user)

    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = 'afablejrchito@gmail.com'
    app.config['RATELIMIT_STORAGE_URI'] = os.getenv("REDIS_URL", "memory://")
    app.config['MAIL_DEBUG'] = True

    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        raise RuntimeError("Missing mail credentials in .env")

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    socketio.init_app(app)
    limiter.init_app(app)

    # Set default rate limits
    limiter.default_limits = ["100 per day", "20 per hour"]

    # Register Blueprints
    from app.routes import main, auth, request, scan, download_log, analytic, profile
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(request.bp)
    app.register_blueprint(scan.bp)
    app.register_blueprint(download_log.bp)
    app.register_blueprint(analytic.bp)
    app.register_blueprint(profile.bp)

    # Register Jinja filters
    from app.utils.helpers import convert_to_ph_time_only
    app.jinja_env.filters['ph_time_only'] = convert_to_ph_time_only

    return app
