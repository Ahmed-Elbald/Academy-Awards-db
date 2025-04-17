# Import necessary modules and packages
from flask import Flask, redirect, url_for
from extensions import db, bcrypt, jwt
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp 
import os
from dotenv import load_dotenv

load_dotenv()

# Import necessary modules for MySQL connection
import pymysql
pymysql.install_as_MySQLdb()

# Create a Flask application instance
def create_app():

    # Initialize Flask app
    app = Flask(__name__)

    # Configurations
    app.secret_key = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')


    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)

    # Index route
    @app.route('/', methods=['GET', 'POST'])
    def index():
        return redirect(url_for('auth.login'))

    return app



if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
