# Import necessary modules and packages
from flask import Blueprint, request, render_template, redirect, url_for, session
from extensions import db, bcrypt
from models.models import User

# Create a blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# Registration route (renders register.html)
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():

    # Check if user is already logged in, and handle accordingly
    if 'username' in session:
        return redirect(url_for('dashboard.dashboard'))

    # Handle POST request for registration
    if request.method == 'POST':

        # Get form data
        data = request.form

        # Validate required fields
        for key in data:
            if not data[key]:
                return render_template('register.html', errors=[f'{key} is required'])

        # Extract data from form
        username = data.get('username')
        email = data.get('email')
        country = data.get('country')
        birthdate = data.get('birthdate')
        gender = data.get('gender')
        _password = data.get('password')
        password_confirm = data.get('password-confirm')

        # Validate password confirmation
        if _password != password_confirm:
            return render_template('register.html', errors=['Passwords do not match'])

        # Validate password strength (at least 8 characters)
        if len(_password) < 8:
            return render_template('register.html', errors=['Password must be at least 8 characters long'])
        
        # Check if user already exists, and handle accordingly
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', errors=['Username already in use'])

        # Hash password and save user
        password_hash = bcrypt.generate_password_hash(_password).decode('utf-8')
        new_user = User(
            username=username, email=email, country=country, birthdate=birthdate, gender=gender, password=password_hash
        )

        # Add new user to the database
        db.session.add(new_user)
        db.session.commit()
        db.session.close()

        # Redirect to login page after registration
        return redirect(url_for('auth.login'))

    # Render the registration page for GET request
    return render_template('register.html')

# Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    # Check if user is already logged in, and handle accordingly
    if 'username' in session:
        return redirect(url_for('dashboard.dashboard'))

    # Handle POST request for login
    if request.method == 'POST':

        # Get form data
        data = request.form

        # Validate required fields
        username = data.get('username')
        _password = data.get('password')

        # Check correctness of username and password
        user = User.query.filter_by(username=username).first()
        if not user or not bcrypt.check_password_hash(user.password, _password):
            return render_template('login.html', errors=['Invalid username or password'])

        # Set session variables upon successful login
        session['username'] = user.username 

        # Redirect to dashboard after successful login
        return redirect(url_for('dashboard.dashboard'))

    # Render the login page for GET request
    return render_template('login.html')


# Logout route
@auth_bp.route('/logout')
def logout():

    # Check if user is logged in, and handle accordingly
    session.pop('username', None)

    # Redirect to login page after logout
    return redirect(url_for('auth.login'))