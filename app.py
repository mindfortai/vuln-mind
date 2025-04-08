import os
import subprocess
import re  # For basic regex validation
from flask import Flask, request, redirect, Response, render_template_string, flash, url_for, session, make_response
from markupsafe import Markup, escape
import pickle
import hashlib
import base64
from werkzeug.utils import secure_filename
import time  # For timestamp generation
import random  # For session token generation
import json  # For user data serialization

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'py', 'html'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'trendy-tees-session-key-789' # Still hardcoded
HARDCODED_API_KEY = "TT-INTERNAL-API-KEY-ABC123XYZ" # Still hardcoded

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Simple User Management (with vulnerabilities) ---

# VULNERABILITY: Users stored in memory and passwords in plaintext
USERS = {
    # Default admin account
    'admin': {
        'password': 'admin123',  # VULNERABILITY: Weak default password
        'email': 'admin@trendytees.com',
        'role': 'admin',
        'created_at': time.time(),
    }
}

# VULNERABILITY: No password complexity requirements
def is_valid_password(password):
    # Only checking length, not complexity
    return len(password) >= 4  # VULNERABILITY: Very short minimum password

# VULNERABILITY: Email validation is too permissive
def is_valid_email(email):
    # Simple check for @ symbol, not proper validation
    return '@' in email

# --- Session Management ---
def generate_session_token():
    # VULNERABILITY: Predictable session token pattern
    return 'session_' + str(int(time.time())) + str(random.randint(1000, 9999))

# --- UI Templates ---

def get_user_nav():
    """Returns HTML for user-related navigation items."""
    if 'username' in session:
        # User is logged in
        return f'''
        <span class="user-nav">
            <a href="/profile">Hi, {escape(session['username'])}</a> | 
            <a href="/logout">Log Out</a>
        </span>
        '''
    else:
        return '<span class="user-nav"><a href="/login">Login</a> | <a href="/register">Register</a></span>'

def render_page(title, content, current_page=None):
    """Helper function to wrap content in a basic Ecommerce HTML structure."""

    # Navigation links - make them sound standard
    nav_links = {
        'home': '/',
        'designs': '#designs',
        'upload_design': '/upload',
        'order_status': '/sql?id=1'
    }
    nav_html = ""
    for name, url in nav_links.items():
        active_class = 'active' if name == current_page else ''
        # Make names user-friendly
        display_name = name.replace("_", " ").title()
        if name == 'designs': display_name = 'Our Designs'
        if name == 'upload_design': display_name = 'Upload Your Design'
        if name == 'order_status': display_name = 'Order Status'

        nav_html += f'<a href="{url}" class="{active_class}">{display_name}</a> '

    user_nav = get_user_nav()

    # Keep the same overall structure but add user navigation
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>{escape(title)} - Trendy Tees</title>
        {get_styles()}
    </head>
    <body>
        <header class="header">
             <h1><a href="/">Trendy Tees</a></h1>
             <nav class="navbar">
                {nav_html}
                {user_nav}
             </nav>
        </header>

        <div class="container">
            <main class="main-content">
                <h2>{escape(title)}</h2>
                {content}
            </main>
        </div>

        <footer class="footer">
            <p>&copy; 2024 Trendy Tees - Custom Apparel</p>
        </footer>
    </body>
    </html>
    """

def get_styles():
    """Returns the CSS styles as a string, with added user management styles."""
    return """
        <style>
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; background-color: #ffffff; color: #333; line-height: 1.6; }
            .header { background-color: #2c3e50; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header h1 a { color: white; text-decoration: none; font-size: 1.6rem; font-weight: bold; }
            .navbar { display: flex; align-items: center; }
            .navbar a { color: #ecf0f1; text-decoration: none; margin-left: 1.5rem; font-size: 1rem; transition: color 0.2s ease; }
            .navbar a:hover, .navbar a.active { color: #1abc9c; }
            .user-nav { margin-left: 2rem; color: #bdc3c7; }
            .user-nav a { color: #3498db; font-size: 0.9rem; }
            .container { max-width: 1200px; margin: 2.5rem auto; padding: 0 1rem; }
            .main-content { background-color: #ffffff; padding: 2.5rem; border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.05); margin-bottom: 2rem; }
            .content-section { margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid #ecf0f1; }
            .content-section:last-child { border-bottom: none; margin-bottom: 0; }
            .content-section h2, .content-section h3 { color: #2c3e50; margin-top: 0; font-weight: 500;}
            .content-section h2 { font-size: 1.8rem; margin-bottom: 1.2rem; }
            .content-section h3 { font-size: 1.3rem; margin-bottom: 1rem; color: #34495e; }
            ul { list-style: none; padding-left: 0; }
            li { margin-bottom: 0.7rem; padding-left: 1.2em; position: relative; }
            li::before { content: '•'; color: #1abc9c; font-weight: bold; display: inline-block; width: 1em; margin-left: -1.2em; position: absolute; }
            a { color: #3498db; text-decoration: none; transition: color 0.2s ease; }
            a:hover { color: #2980b9; text-decoration: underline; }
            .footer { text-align: center; margin-top: 4rem; padding: 2rem; background-color: #ecf0f1; color: #7f8c8d; font-size: 0.9em; border-top: 1px solid #dcdcdc; }
            .card { border: 1px solid #ecf0f1; border-radius: 5px; padding: 2rem; margin-bottom: 2rem; background-color: #fdfdfd; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
            .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 2rem; margin-top: 1.5rem; }
            .product-card { border: 1px solid #ecf0f1; border-radius: 5px; padding: 1.5rem; text-align: center; background-color: #fff; transition: box-shadow 0.2s ease; }
            .product-card:hover { box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .product-card img { max-width: 100%; height: auto; margin-bottom: 1rem; border-radius: 4px; }
            .product-card h4 { margin: 1rem 0 0.5rem 0; color: #2c3e50; font-size: 1.1rem; }
            .product-card .price { font-weight: bold; color: #27ae60; margin-bottom: 1.5rem; font-size: 1.2rem; }
            .btn { display: inline-block; font-weight: 500; color: #fff; text-align: center; vertical-align: middle; user-select: none; background-color: #3498db; border: 1px solid #3498db; padding: .5rem 1.2rem; font-size: 1rem; line-height: 1.5; border-radius: .25rem; transition: all .15s ease-in-out; text-decoration: none; cursor: pointer; }
            .btn:hover { background-color: #2980b9; border-color: #2980b9; }
            .btn-secondary { background-color: #7f8c8d; border-color: #7f8c8d; }
            .btn-secondary:hover { background-color: #6c7a89; border-color: #6c7a89; }
            pre { background-color: #ecf0f1; padding: 15px; border: 1px solid #dcdcdc; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', Courier, monospace; font-size: 0.9em; color: #333; }
            .flash { padding: 1rem 1.5rem; margin-bottom: 1.5rem; border-radius: 4px; border: 1px solid transparent; }
            .flash.success { background-color: #d4edda; color: #155724; border-color: #c3e6cb; }
            .flash.error { background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }
            .flash.info { background-color: #cce5ff; color: #004085; border-color: #b8daff; }
            form label { display: block; margin-bottom: .6rem; font-weight: bold; color: #34495e; }
            form input[type=file], form input[type=text], form input[type=password], form input[type=email] { width: 100%; padding: .6rem .9rem; margin-bottom: 1rem; font-size: 1rem; line-height: 1.5; color: #495057; background-color: #fff; background-clip: padding-box; border: 1px solid #ced4da; border-radius: .25rem; transition: border-color .15s ease-in-out,box-shadow .15s ease-in-out; box-sizing: border-box; }
            form input[type=submit] { margin-top: 1rem; }
            code { background-color: #ecf0f1; padding: 3px 6px; border-radius: 3px; font-family: 'Courier New', Courier, monospace; color: #c0392b; }
            .form-group { margin-bottom: 1rem; }
            .profile-info { line-height: 1.8; }
            .profile-info dt { font-weight: bold; margin-top: 1rem; }
            .profile-info dd { margin-left: 0; color: #34495e; }
        </style>
    """

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Modified homepage to check for session."""
    # Welcome message based on login status
    welcome_msg = ""
    if 'username' in session:
        welcome_msg = f"<p>Welcome back, <strong>{escape(session['username'])}</strong>! "
        welcome_msg += "Find the perfect custom t-shirt or browse our collection.</p>"
    else:
        welcome_msg = "<p>Welcome to Trendy Tees! Find the perfect custom t-shirt or browse our unique collection.</p>"
        welcome_msg += "<p><a href='/login' class='btn'>Log In</a> or <a href='/register' class='btn btn-secondary'>Create Account</a></p>"

    try:
        dummy_data = {'wishlist_id': 'wl-abc-789', 'items': ['T001', 'T004']}
        pickled_data = pickle.dumps(dummy_data)
        encoded_pickle = base64.urlsafe_b64encode(pickled_data).decode('utf-8')
    except Exception:
        encoded_pickle = ""

    content = f"""
    {welcome_msg}

    <div id="designs" class="content-section">
        <h3>Shop Our Designs</h3>
        <div class="product-grid">
            <div class="product-card">
                 <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='150' viewBox='0 0 200 150'%3E%3Crect width='100%25' height='100%25' fill='%23cccccc'/%3E%3Ctext x='50%25' y='50%25' fill='%23ffffff' dominant-baseline='middle' text-anchor='middle' font-size='16px'%3ETee Placeholder%3C/text%3E%3C/svg%3E" alt="T-Shirt Placeholder">
                <h4>Classic Crew Neck</h4>
                <p class="price">$19.99</p>
                <a href="/lfi?file=classic_crew_neck_specs.txt" class="btn">View Details</a>
            </div>
            <div class="product-card">
                 <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='150' viewBox='0 0 200 150'%3E%3Crect width='100%25' height='100%25' fill='%23cccccc'/%3E%3Ctext x='50%25' y='50%25' fill='%23ffffff' dominant-baseline='middle' text-anchor='middle' font-size='16px'%3ETee Placeholder%3C/text%3E%3C/svg%3E" alt="T-Shirt Placeholder">
                <h4>Custom Message Tee</h4>
                <p class="price">$24.99</p>
                <a href="/ssti?name=Your%20Message%20Here" class="btn">Personalize</a>
            </div>
             <div class="product-card">
                 <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='150' viewBox='0 0 200 150'%3E%3Crect width='100%25' height='100%25' fill='%23cccccc'/%3E%3Ctext x='50%25' y='50%25' fill='%23ffffff' dominant-baseline='middle' text-anchor='middle' font-size='16px'%3ETee Placeholder%3C/text%3E%3C/svg%3E" alt="T-Shirt Placeholder">
                <h4>Search Slogan Tee</h4>
                 <p class="price">$21.99</p>
                 <a href="/xss?input=ExampleSlogan" class="btn">Preview Slogan</a>
            </div>
             <div class="product-card">
                 <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='150' viewBox='0 0 200 150'%3E%3Crect width='100%25' height='100%25' fill='%23cccccc'/%3E%3Ctext x='50%25' y='50%25' fill='%23ffffff' dominant-baseline='middle' text-anchor='middle' font-size='16px'%3ETee Placeholder%3C/text%3E%3C/svg%3E" alt="T-Shirt Placeholder">
                <h4>Supplier Info Link</h4>
                 <p class="price">N/A</p>
                 <a href="/redirect?url=https://example.com/supplier-portal" class="btn btn-secondary">Visit Supplier</a>
            </div>
        </div>
    </div>

    <div id="tools" class="content-section">
        <h3>Customer Tools</h3>
        <ul>
            <li><strong>Order Status:</strong> Check your <a href="/sql?id=12345">Order Status by ID</a>.</li>
            <li><strong>Load Wishlist:</strong> <a href="/deserialize?data={encoded_pickle}">Load Your Saved Wishlist</a>.</li>
             <li><strong>Get Order Code:</strong> <a href="/weak_hash?data=order12345">Generate Simple Code</a> for order 'order12345'.</li>
            <li><strong>Upload Custom Design:</strong> <a href="/upload">Upload Your Artwork</a>.</li>
            <li><small><em>Internal Use:</em> <a href="/command?cmd=id">System Check</a></small></li>
        </ul>
    </div>
    """
    return render_page("Home", content, current_page='home')

# --- Vulnerability Routes (Wrapped & Obfuscated) ---

@app.route('/lfi')
def lfi():
    # Reframe as viewing product details
    filename = request.args.get('file')
    title = "T-Shirt Details"
    if not filename:
        content = "<p class='flash error'>No product specified.</p>"
        return render_page(title + " Error", content), 400

    # --- LFI Vulnerability Preserved ---
    # For the demo, it still reads app.py regardless of input, but pretends based on filename
    safe_filename_to_read = os.path.basename(__file__) # Secretly reads this file
    file_path = os.path.join(os.path.dirname(__file__), safe_filename_to_read)
    # ---

    file_content_html = ""
    status_code = 200
    try:
        # Check if the *secretly* read file exists
        if os.path.exists(file_path) and os.path.abspath(file_path) == os.path.abspath(__file__):
             with open(file_path, 'r') as f:
                content_data = f.read()
             # Pretend the content is for the requested filename
             file_content_html = f"<h3>Details for '{escape(filename)}':</h3><pre>{escape(content_data)}</pre>"
             file_content_html += f"<p class='flash info'>Displaying default details. File requested: '{escape(filename)}'.</p>" # Less alarming message
        else:
             file_content_html = f"<p class='flash error'>Could not load details for '{escape(filename)}'.</p>"
             status_code = 404 # More appropriate error
    except Exception as e:
        # Generic error
        file_content_html = f"<p class='flash error'>An error occurred loading product details.</p>"
        print(f"LFI route error: {e}") # Log real error for debugging if needed
        status_code = 500

    # Don't show debug info to regular users
    return render_page(title, file_content_html), status_code

@app.route('/ssti')
def ssti():
    # Reframe as custom message preview
    name = request.args.get('name', 'Your Text Here')
    title = "Custom Message Preview"
    # --- SSTI Vulnerability Preserved ---
    # Template string still includes raw user input via f-string
    template_string = f"<h3>Your Custom Message:</h3><div class='card' style='font-size: 1.5em; text-align: center;'>{name}</div><p>Enter your desired message in the 'name' parameter in the URL.</p>"
    # ---
    try:
        # render_template_string still processes the user input
        rendered_template = render_template_string(template_string)
        return render_page(title, rendered_template)
    except Exception as e:
        error_content = f"<p class='flash error'>Could not preview message.</p><p>Input: {escape(name)}</p>"
        print(f"SSTI route error: {e}") # Log real error
        return render_page(title + " Error", error_content), 500

@app.route('/redirect')
def open_redirect():
    # Reframe as redirecting to a partner/supplier
    redirect_url = request.args.get('url')
    title = "Redirecting..."
    if redirect_url:
        # --- Open Redirect Vulnerability Preserved ---
        return redirect(redirect_url, code=302)
    else:
        content = "<p class='flash error'>Redirect target missing.</p>"
        return render_page(title + " Error", content), 400

@app.route('/xss')
def reflected_xss():
    # Reframe as search result or slogan preview
    user_input = request.args.get('input', '')
    title = "Slogan Preview"
    # --- XSS Vulnerability Preserved ---
    # Markup() still disables escaping for user_input
    response_html_content = f"<h3>Previewing Slogan:</h3><div class='card'>{Markup(user_input)}</div><p>Your slogan is shown above. Use the 'input' parameter in the URL.</p>"
    # ---
    return render_page(title, response_html_content)

@app.route('/command')
def command_injection():
    # Reframe as an internal tool, less visible
    command_param = request.args.get('cmd')
    title = "Internal System Check"
    output_html = "<p>Internal tool. Requires specific commands.</p>" # Vague message

    if command_param:
        allowed_commands = {'id', 'pwd'} # Keep restriction for safety
        if command_param in allowed_commands:
            try:
                # --- Command Injection Pattern Preserved (but restricted) ---
                result = subprocess.run([command_param], capture_output=True, text=True, check=True, shell=False)
                output_html = f"<h3>Check Result '{escape(command_param)}':</h3><pre>{escape(result.stdout)}</pre>"
            except Exception as e:
                output_html = f"<p class='flash error'>Check '{escape(command_param)}' failed.</p>"
                print(f"Command route error: {e}") # Log real error
        else:
            output_html = f"<p class='flash error'>Command '{escape(command_param)}' not recognized.</p>"

    return render_page(title, output_html) # Don't show debug info

@app.route('/sql')
def sql_injection_pattern():
    # Reframe as order lookup
    user_id = request.args.get('id', '0') # Default to 0 or invalid ID
    title = "Order Status"
    # --- SQLi Pattern Preserved ---
    # Unsafe query string construction remains
    simulated_query = f"SELECT status, ship_date FROM orders WHERE order_id = {user_id};"
    # ---
    content = f"""
    <p>Checking status for Order ID: <code>{escape(user_id)}</code></p>
    
    <div class='card'>
        <h4>Simulated Status:</h4>
        <p>Query Sent: <code>{escape(simulated_query)}</code></p>
        <p>Result: <strong>{'Shipped' if user_id == '12345' else 'Processing / Not Found'}</strong></p>
    </div>
    <p><small>Enter your Order ID in the 'id' parameter in the URL.</small></p>
    """
    return render_page(title, content)

@app.route('/deserialize')
def insecure_deserialization():
    # Reframe as loading a saved wishlist
    encoded_data = request.args.get('data')
    title = "Load Wishlist"
    result_html = ""
    status_code = 200

    if not encoded_data:
        result_html = "<p class='flash info'>Use the 'data' parameter to load a saved wishlist code.</p>"
        # Don't return 400, just show info message
    else:
        try:
            pickled_data = base64.urlsafe_b64decode(encoded_data)
            # --- Deserialization Vulnerability Preserved ---
            deserialized_object = pickle.loads(pickled_data)
            result_html = f"<h3>Wishlist Loaded</h3><p>Items:</p><pre>{escape(str(deserialized_object))}</pre>"
            # ---
        except Exception as e:
            result_html = f"<p class='flash error'>Could not load wishlist from the provided code.</p>"
            print(f"Deserialize route error: {e}") # Log real error
            status_code = 400 # Error on bad data

    return render_page(title, result_html), status_code

@app.route('/weak_hash')
def weak_hash():
    # Reframe as generating a simple order code
    data_to_hash = request.args.get('data', 'orderXYZ')
    title = "Order Code Generator"
    # --- Weak Hash Vulnerability Preserved ---
    hasher = hashlib.md5()
    hasher.update(data_to_hash.encode('utf-8'))
    weak_hash_result = hasher.hexdigest()[:8] # Take only first 8 chars to look less like a hash
    # ---
    content = f"""
    <p>Generating a simple reference code for input: <code>{escape(data_to_hash)}</code></p>
    <p>Your Code: <strong>{escape(weak_hash_result)}</strong></p>
    <p><small>Provide input via the 'data' parameter in the URL.</small></p>
    """
    return render_page(title, content)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # Reframe as uploading a custom t-shirt design
    title = "Upload Your T-Shirt Design"
    upload_form_html = f'''
    <p>Upload your artwork here. Allowed types: {escape(str(ALLOWED_EXTENSIONS))}.</p>
    <form method=post enctype=multipart/form-data class="card">
      <label for="file">Choose image file:</label>
      <input type=file name=file id="file" accept="image/*,.txt,.pdf,.py,.html"> <!-- Slightly better hint -->
      <input type=submit value="Upload Design" class="btn">
    </form>
    <p><small>Your design will be processed shortly.</small></p>
    '''

    messages_html = ""
    if '_flashes' in session:
         flashed_messages = session.pop('_flashes')
         for category, message in flashed_messages:
             # Make messages less specific about errors if needed
             display_message = message
             if 'Error saving' in message: display_message = "An error occurred during upload."
             elif 'Invalid file type' in message: display_message = "Invalid file type."
             messages_html += f'<div class="flash {category}">{escape(display_message)}</div>'

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part selected.', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for upload.', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # --- File Upload Vulnerability Preserved ---
            filename = secure_filename(file.filename) # Basic sanitization still used
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) # Saved to predictable location
            try:
                file.save(save_path) # Actual save operation
                flash(f'Design "{filename}" uploaded successfully!', 'success')
            except Exception as e:
                 flash(f'Error saving design.', 'error') # Generic error message
                 print(f"Upload route error: {e}") # Log real error
            return redirect(url_for('upload_file'))
            # ---
        else:
            flash(f'Invalid file type.', 'error') # Generic error
            return redirect(request.url)

    # GET request
    return render_page(title, messages_html + upload_form_html, current_page='upload_design')

# --- User Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()

        error = None

        # VULNERABILITY: User enumeration through different error messages
        if not username or not password or not email:
            error = "All fields are required."
        elif username in USERS:
            # VULNERABILITY: This reveals whether a username exists
            error = f"Username '{username}' is already taken."
        elif not is_valid_email(email):
            error = "Please enter a valid email address."
        elif not is_valid_password(password):
            error = "Password must be at least 4 characters long."
        
        if error:
            flash(error, 'error')
            return redirect(url_for('register'))
        
        # Create the user
        USERS[username] = {
            'password': password,  # VULNERABILITY: Stored in plaintext
            'email': email,
            'role': 'user',
            'created_at': time.time(),
        }

        flash(f"Registration successful! Welcome {username}.", 'success')
        # Log the user in
        session['username'] = username
        # VULNERABILITY: Session fixation - we don't regenerate the session token after login
        
        return redirect(url_for('index'))
    
    # GET request, show registration form
    registration_form = '''
    <div class="card">
        <h3>Create an Account</h3>
        <form method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                <small>Must be at least 4 characters long.</small>
            </div>
            <input type="submit" value="Register" class="btn">
        </form>
        <p>Already have an account? <a href="/login">Log in</a></p>
    </div>
    '''
    return render_page("Register", registration_form)

# --- User Login Route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # VULNERABILITY: Timing attack possible here (though hard to exploit in practice)
        if username in USERS and password == USERS[username]['password']:
            session['username'] = username
            # VULNERABILITY: Session fixation - not regenerating session ID after login
            
            flash(f"Welcome back, {username}!", 'success')
            return redirect(url_for('index'))
        else:
            # VULNERABILITY: Generic error message helps prevent user enumeration
            flash("Invalid username or password. Please try again.", 'error')
            return redirect(url_for('login'))
    
    # GET request, show login form
    login_form = '''
    <div class="card">
        <h3>Log In</h3>
        <form method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <input type="submit" value="Log In" class="btn">
        </form>
        <p>Don't have an account? <a href="/register">Register</a></p>
    </div>
    '''
    return render_page("Login", login_form)

# --- Logout Route ---
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", 'success')
    
    # Redirect with a 'next' parameter (VULNERABILITY: Open redirect if not validated)
    next_url = request.args.get('next', url_for('index'))
    
    # VULNERABILITY: No validation of 'next' parameter - could be used for open redirect
    return redirect(next_url)

# --- User Profile Route ---
@app.route('/profile')
@app.route('/profile/<username>')
def profile(username=None):
    # If no username provided, use currently logged in user
    if username is None:
        if 'username' not in session:
            flash("Please log in to view your profile.", 'error')
            return redirect(url_for('login'))
        username = session['username']
    
    # VULNERABILITY: IDOR - Can view any user's profile by manipulating URL
    if username not in USERS:
        flash(f"User '{username}' not found.", 'error')
        return redirect(url_for('index'))
    
    user_data = USERS[username]
    is_own_profile = 'username' in session and session['username'] == username
    is_admin = 'username' in session and USERS.get(session['username'], {}).get('role') == 'admin'
    
    # Create formatted date/time from timestamp
    created_date = time.strftime("%Y-%m-%d", time.localtime(user_data.get('created_at', 0)))
    
    profile_content = f'''
    <div class="card">
        <h3>User Profile: {escape(username)}</h3>
        <dl class="profile-info">
            <dt>Username:</dt>
            <dd>{escape(username)}</dd>
            
            <dt>Email:</dt>
            <dd>{escape(user_data.get('email', 'N/A'))}</dd>
            
            <dt>Role:</dt>
            <dd>{escape(user_data.get('role', 'user'))}</dd>
            
            <dt>Member Since:</dt>
            <dd>{escape(created_date)}</dd>
        </dl>
        
        <!-- VULNERABILITY: Exposing sensitive information to administrators -->
        {f"<p><strong>Admin Panel:</strong> <a href='/admin/users'>Manage Users</a></p>" if is_admin else ""}
        
        <!-- VULNERABILITY: User ID in URL could allow enumeration -->
        {f"<a href='/profile/{username}?format=json' class='btn btn-secondary'>View as JSON</a>" if is_admin or is_own_profile else ""}
    </div>
    '''
    
    # VULNERABILITY: JSON data disclosure if requested
    if request.args.get('format') == 'json':
        # VULNERABILITY: Detailed user data exposed via JSON without sanitization
        # This would allow access to all user data fields
        json_data = json.dumps(user_data)
        return Response(json_data, mimetype='application/json')
    
    return render_page(f"Profile: {username}", profile_content)

# --- Admin Panel Route ---
@app.route('/admin/users')
def admin_users():
    if 'username' not in session or USERS.get(session['username'], {}).get('role') != 'admin':
        flash("Access denied. Admin privileges required.", 'error')
        return redirect(url_for('index'))
    
    # VULNERABILITY: Showing all user data including passwords
    users_list = "<ul>"
    for username, data in USERS.items():
        users_list += f"<li><strong>{escape(username)}</strong> ({escape(data['email'])}) - Role: {escape(data['role'])}, Password: {escape(data['password'])}</li>"
    users_list += "</ul>"
    
    admin_content = f'''
    <div class="card">
        <h3>User Management</h3>
        <p>Total users: {len(USERS)}</p>
        {users_list}
    </div>
    '''
    
    return render_page("Admin: User Management", admin_content)

if __name__ == '__main__':
    print("Starting Trendy Tees online store...")
    print(f"Store running at http://0.0.0.0:5001")
    # Default admin user credentials reminder
    print(f"Default admin credentials: username='admin', password='admin123'")
    app.run(debug=True, host='0.0.0.0', port=5001)
