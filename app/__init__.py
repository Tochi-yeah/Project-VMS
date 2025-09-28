# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# Temporarily removed 
#from flask_mail import Mail
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_login import LoginManager
import os

load_dotenv()  # Load environment variables from .env file

# Global extensions
db = SQLAlchemy()
#Removed temporarily
#mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")  # Add this line
limiter = Limiter(key_func=get_remote_address)  # make global instance
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # the name of your login route

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'),
         static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
    )
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY')
    app.config['RATELIMIT_STORAGE_URI'] = os.getenv("REDIS_URL", "memory://")
    '''
    Temporarily removed
    # Mail Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = 'afablejrchito@gmail.com'
    app.config['RATELIMIT_STORAGE_URI'] = os.getenv("REDIS_URL", "memory://")
    app.config['MAIL_DEBUG'] = True
    '''
    
    # Connection Pool Management for Render/Eventlet/Psycopg2
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_size": 10,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_recycle": 1800  # recycle connections_
    }

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True
    }
    #Temporarily Removed
    '''
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        raise RuntimeError("Missing mail credentials in .env")
    '''

    # Initialize extensions
    db.init_app(app)
    #Removed temporarily
    #mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    socketio.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)

    # Set default rate limits
    limiter.default_limits = ["100 per day", "20 per hour"]

    # Register Blueprints
    from app.routes import main, auth, request, scan, download_log, analytic, profile, download_template
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(request.bp)
    app.register_blueprint(scan.bp)
    app.register_blueprint(download_log.bp)
    app.register_blueprint(analytic.bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(download_template.bp) # ✅ Register the new blueprint

    from app.models import User

    # Register Jinja filters
    from app.utils.helpers import convert_to_ph_time_only
    app.jinja_env.filters['ph_time_only'] = convert_to_ph_time_only

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app
