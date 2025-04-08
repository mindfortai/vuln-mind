import os
import subprocess
from flask import Flask, request, redirect, Response, render_template_string, flash, url_for, session
from markupsafe import Markup, escape
import pickle
import hashlib
import base64
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'py', 'html'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'insecure-ecommerce-key-456' # Still a hardcoded secret
HARDCODED_API_KEY = "EKIAIOSFODNN7EXAMPLE-ECOMMERCE" # Different hardcoded secret

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Ecommerce UI Templating ---

def render_page(title, content, show_debug_info=False, current_page=None):
    """Helper function to wrap content in a basic Ecommerce HTML structure."""
    debug_html = ""
    if show_debug_info:
        params_html = "".join([f"<li>{escape(k)}: {escape(v)}</li>" for k, v in request.args.items()])
        debug_html = f"""
        <div class="debug-info card">
            <h4>Request Debug Info (Demo Only)</h4>
            <p><strong>Query Parameters:</strong></p>
            <ul>{params_html if params_html else '<li>None</li>'}</ul>
        </div>
        """

    nav_links = {
        'home': '/',
        'products': '#products', # Anchor link on homepage
        'upload': '/upload',
        'account': '#account-demos' # Anchor link on homepage
    }
    nav_html = ""
    for name, url in nav_links.items():
        active_class = 'active' if name == current_page else ''
        nav_html += f'<a href="{url}" class="{active_class}">{name.replace("_", " ").title()}</a> '

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>{escape(title)} - Vulnerable Emporium</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background-color: #f8f9fa; color: #212529; line-height: 1.6; }}
            .header {{ background-color: #007bff; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 a {{ color: white; text-decoration: none; font-size: 1.5rem; }}
            .navbar {{ }} /* Removed specific navbar styles, integrated into header */
            .navbar a {{ color: #e9ecef; text-decoration: none; margin-left: 1.5rem; font-size: 1rem; }}
            .navbar a:hover, .navbar a.active {{ color: white; text-decoration: underline; }}
            .container {{ max-width: 1140px; margin: 2rem auto; padding: 0 1rem; }}
            .main-content {{ background-color: #ffffff; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.075); margin-bottom: 2rem; }}
            .content-section {{ margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #dee2e6; }}
            .content-section:last-child {{ border-bottom: none; margin-bottom: 0; }}
            .content-section h2, .content-section h3 {{ color: #0056b3; margin-top: 0; }}
            .content-section h2 {{ font-size: 1.75rem; margin-bottom: 1rem; }}
            .content-section h3 {{ font-size: 1.25rem; margin-bottom: 0.75rem; }}
            ul {{ list-style: disc; padding-left: 20px; }} /* Changed list style */
            li {{ margin-bottom: 0.6rem; }}
            a {{ color: #007bff; }}
            a:hover {{ color: #0056b3; text-decoration: none; }} /* Remove underline on hover for general links */
            .footer {{ text-align: center; margin-top: 3rem; padding: 1.5rem; background-color: #e9ecef; color: #6c757d; font-size: 0.9em; border-top: 1px solid #dee2e6; }}
            .card {{ border: 1px solid #dee2e6; border-radius: 5px; padding: 1.5rem; margin-bottom: 1.5rem; background-color: #f8f9fa; }}
            .product-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-top: 1.5rem; }}
            .product-card {{ border: 1px solid #dee2e6; border-radius: 5px; padding: 1rem; text-align: center; background-color: #fff; }}
            .product-card img {{ max-width: 100%; height: auto; margin-bottom: 1rem; }}
            .product-card h4 {{ margin: 0.5rem 0; color: #343a40; }}
            .product-card .price {{ font-weight: bold; color: #28a745; margin-bottom: 1rem; }}
            .btn {{ display: inline-block; font-weight: 400; color: #fff; text-align: center; vertical-align: middle; user-select: none; background-color: #007bff; border: 1px solid #007bff; padding: .375rem .75rem; font-size: 1rem; line-height: 1.5; border-radius: .25rem; transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out; text-decoration: none; cursor: pointer; }}
            .btn:hover {{ background-color: #0056b3; border-color: #004085; }}
            .debug-info {{ background-color: #fff3cd; border-color: #ffeeba; color: #856404; font-size: 0.9em; }}
            pre {{ background-color: #e9ecef; padding: 15px; border: 1px solid #ced4da; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-family: monospace; font-size: 0.95em; }}
            .flash {{ padding: 1rem 1.5rem; margin-bottom: 1.5rem; border-radius: 4px; border: 1px solid transparent; }}
            .flash.success {{ background-color: #d1e7dd; color: #0f5132; border-color: #badbcc; }}
            .flash.error {{ background-color: #f8d7da; color: #842029; border-color: #f5c2c7; }}
            .warning {{ color: #dc3545; font-weight: bold; }}
            form label {{ display: block; margin-bottom: .5rem; font-weight: bold; }}
            form input[type=file], form input[type=submit] {{ margin-top: 1rem; }}
            form input[type=text], form input[type=password] {{ width: 100%; padding: .375rem .75rem; margin-bottom: 1rem; font-size: 1rem; line-height: 1.5; color: #495057; background-color: #fff; background-clip: padding-box; border: 1px solid #ced4da; border-radius: .25rem; transition: border-color .15s ease-in-out,box-shadow .15s ease-in-out; box-sizing: border-box; }} /* Added box-sizing */
            code {{ background-color: rgba(0,0,0,0.05); padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
        </style>
    </head>
    <body>
        <header class="header">
             <h1><a href="/">Vulnerable Emporium</a></h1>
             <nav class="navbar">
                {nav_html}
             </nav>
        </header>

        <div class="container">
            <main class="main-content">
                <h2>{escape(title)}</h2>
                {debug_html}
                {content}
            </main>
        </div>

        <footer class="footer">
            <p>&copy; 2024 Vulnerable Emporium - Not a Real Store</p>
            <p>Flask Debug Mode: {'ON' if app.debug else 'OFF'} | For security testing purposes only.</p>
        </footer>
    </body>
    </html>
    """

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serves the themed ecommerce homepage."""
    try:
        dummy_data = {'user': 'admin', 'cart_id': 'xyz123'}
        pickled_data = pickle.dumps(dummy_data)
        encoded_pickle = base64.urlsafe_b64encode(pickled_data).decode('utf-8')
    except Exception:
        encoded_pickle = "error_encoding_pickle"

    content = f"""
    <p>Welcome to the Vulnerable Emporium! Your one-stop shop for... testing security tools.</p>

    <div id="products" class="content-section">
        <h3>Featured Products (Security Demo Links)</h3>
        <div class="product-grid">
            <div class="product-card">
                <h4>Product Specs Doc</h4>
                <p><small>LFI Demo</small></p>
                <p class="price">$0.00</p>
                <a href="/lfi?file=app.py" class="btn">View Details (app.py)</a><br>
                <a href="/lfi?file=../../uploads/test.txt" style="font-size:0.8em; margin-top: 5px; display:inline-block;">(Try reading upload)</a>
            </div>
            <div class="product-card">
                <h4>Custom Greeting Card</h4>
                 <p><small>SSTI Demo</small></p>
                 <p class="price">$0.00</p>
                 <a href="/ssti?name={{{{config}}}}" class="btn">Personalize (Config)</a><br>
                 <a href="/ssti?name=Customer" style="font-size:0.8em; margin-top: 5px; display:inline-block;">(Try 'Customer')</a>
            </div>
             <div class="product-card">
                <h4>"Anything Goes" Echo T-Shirt</h4>
                 <p><small>XSS Demo</small></p>
                 <p class="price">$0.00</p>
                 <a href="/xss?input=<img src=x onerror=alert('XSS!')>" class="btn">Customize Slogan</a>
            </div>
             <div class="product-card">
                <h4>Partner Site Redirector</h4>
                 <p><small>Open Redirect Demo</small></p>
                 <p class="price">$0.00</p>
                 <a href="/redirect?url=https://example.com" class="btn">Visit Partner</a>
            </div>
        </div>
    </div>

    <div id="account-demos" class="content-section">
        <h3>Account & Tools (More Demos)</h3>
        <ul>
            <li><strong>Order Lookup (SQLi Pattern):</strong> <a href="/sql?id=1">View Order 1</a> | <a href="/sql?id=1%20OR%201=1">Try SQLi Payload</a></li>
            <li><strong>System Status Check (Command Injection Demo):</strong> <a href="/command?cmd=id">Run 'id'</a> | <a href="/command?cmd=pwd">Run 'pwd'</a></li>
            <li><strong>Load Saved Cart (Deserialization Demo):</strong> <a href="/deserialize?data={encoded_pickle}">Load Demo Cart</a></li>
            <li><strong>Password Reset Hash (Weak Hash Demo):</strong> <a href="/weak_hash?data=password123">Hash 'password123'</a></li>
            <li><strong>Upload Profile Picture (File Upload Demo):</strong> <a href="/upload">Go to Upload Page</a></li>
        </ul>
    </div>

    <div class="content-section">
        <h3>Security Testing Information</h3>
        <p>This site contains intentional vulnerabilities for testing purposes:</p>
        <h4>Static Analysis (SAST/CodeQL) Focus:</h4>
        <ul>
            <li>Hardcoded SECRET_KEY (<code>{escape(app.config.get('SECRET_KEY','N/A'))}</code>) & API Key (<code>{escape(HARDCODED_API_KEY)}</code>) in source.</li>
            <li>Insecure Deserialization using <code>pickle.loads()</code> in the "Load Saved Cart" feature.</li>
            <li>Use of weak hash <code>hashlib.md5()</code> in the "Password Reset Hash" demo.</li>
            <li>Insecure file upload handling.</li>
            <li>Debug mode enabled.</li>
            <li>Other patterns: Command Injection, SQL Injection, LFI, SSTI, XSS (check route source code).</li>
        </ul>
         <h4>Attack Chains to Try:</h4>
        <ol>
             <li>Upload a file via "Upload Profile Picture", then try to read it via the "Product Specs Doc" LFI (e.g., <code>/lfi?file=../uploads/your_file.txt</code> - restricted).</li>
            <li>Exploit "Custom Greeting Card" SSTI for RCE.</li>
            <li>Craft a malicious pickle object for "Load Saved Cart" RCE.</li>
            <li>Use LFI to read <code>app.py</code> and find secrets.</li>
            <li>Use XSS in "Echo T-Shirt" to simulate session hijacking.</li>
        </ol>
    </div>
    """
    return render_page("Welcome to the Emporium", content, current_page='home')

# --- Vulnerability Routes (Wrapped in Ecommerce UI) ---

@app.route('/lfi')
def lfi():
    filename = request.args.get('file')
    title = "Product Specification Viewer"
    if not filename:
        content = "<p class='flash error'>Error: Please provide a 'file' parameter to specify the product document.</p>"
        return render_page(title + " Error", content), 400

    safe_filename_to_read = os.path.basename(__file__)
    file_path = os.path.join(os.path.dirname(__file__), safe_filename_to_read)

    file_content_html = ""
    status_code = 200
    try:
        if os.path.abspath(file_path) == os.path.abspath(__file__):
             with open(file_path, 'r') as f:
                content_data = f.read()
             file_content_html = f"<h3>Specifications for '{escape(safe_filename_to_read)}' (Demo File):</h3><pre>{escape(content_data)}</pre>"
             if filename != safe_filename_to_read:
                  file_content_html += f"<p class='flash'>Note: Requested specs for '{escape(filename)}', but demo restricted to showing '{escape(safe_filename_to_read)}'. LFI pattern exists.</p>"
        else:
             file_content_html = f"<p class='flash error'>Access Denied (Simulated restriction for file: {escape(filename)}).</p>"
             status_code = 403
    except FileNotFoundError:
        file_content_html = f"<p class='flash error'>Specification document not found: {escape(safe_filename_to_read)}</p>"
        status_code = 404
    except Exception as e:
        file_content_html = f"<p class='flash error'>An error occurred retrieving specs: {escape(str(e))}</p>"
        status_code = 500

    return render_page(title, file_content_html, show_debug_info=True), status_code

@app.route('/ssti')
def ssti():
    name = request.args.get('name', 'Valued Customer')
    title = "Personalized Greeting"
    # Vulnerable template string
    template_string = f"<h3>Hello {name}!</h3><p>Welcome back to the Vulnerable Emporium!</p><p>This greeting uses template rendering. Try SSTI payloads in the 'name' parameter (e.g., <code>?name={{{{config}}}}</code> or <code>?name={{{{7*7}}}}</code>).</p>"
    try:
        rendered_template = render_template_string(template_string)
        return render_page(title, rendered_template, show_debug_info=True)
    except Exception as e:
        error_content = f"<p class='flash error'>Error rendering greeting: {escape(str(e))}</p><p>Original name input: {escape(name)}</p>"
        return render_page(title + " Error", error_content, show_debug_info=True), 500

@app.route('/redirect')
def open_redirect():
    redirect_url = request.args.get('url')
    title = "Redirecting to Partner"
    if redirect_url:
        # --- Vulnerable Code ---
        return redirect(redirect_url, code=302)
    else:
        content = "<p class='flash error'>Error: No partner URL provided.</p>"
        return render_page(title + " Error", content, show_debug_info=True), 400

@app.route('/xss')
def reflected_xss():
    user_input = request.args.get('input', '')
    title = "Custom T-Shirt Slogan Preview"
    # --- Vulnerable Code ---
    response_html_content = f"<h3>Your Custom Slogan:</h3><div class='card'>{Markup(user_input)}</div><hr><p>Slogan rendered directly. Try XSS payloads like <code>&lt;script&gt;alert('XSS')&lt;/script&gt;</code> in the 'input' parameter.</p>"
    # --- End ---
    return render_page(title, response_html_content, show_debug_info=True)

@app.route('/command')
def command_injection():
    command_param = request.args.get('cmd')
    title = "System Status Check (Admin Demo)"
    output_html = "<p>Enter command 'id' or 'pwd' in the URL (e.g., <code>?cmd=id</code>) to check system status.</p>"

    if command_param:
        allowed_commands = {'id', 'pwd'}
        if command_param in allowed_commands:
            try:
                result = subprocess.run([command_param], capture_output=True, text=True, check=True, shell=False)
                output_html = f"<h3>Status Result for '{escape(command_param)}':</h3><pre>{escape(result.stdout)}</pre><p><small>Note: Only 'id' and 'pwd' allowed in this demo. Command injection pattern exists.</small></p>"
            except Exception as e:
                output_html = f"<p class='flash error'>Error running command '{escape(command_param)}': {escape(str(e))}</p>"
        else:
            output_html = f"<p class='flash error'>Command not allowed: '{escape(command_param)}'. Only 'id' or 'pwd' are permitted.</p>"

    return render_page(title, output_html, show_debug_info=True)

@app.route('/sql')
def sql_injection_pattern():
    user_id = request.args.get('id', '1')
    title = "Order Details Lookup"
    # --- Vulnerable Pattern ---
    simulated_query = f"SELECT * FROM orders WHERE order_id = {user_id};" # UNSAFE
    # --- End ---
    content = f"""
    <p>Looking up details for Order ID: <code>{escape(user_id)}</code></p>
    <p>Simulated Database Query (<strong>!! INSECURE - DO NOT USE IN PRODUCTION !!</strong>):</p>
    <pre>{escape(simulated_query)}</pre>
    <p>Try SQLi payloads in the 'id' parameter, like <code>1' OR '1'='1</code> or <code>1 UNION SELECT user, pass FROM admin_table--</code>.</p>
    <p><em>Note: No actual database is connected. This only demonstrates the unsafe query pattern.</em></p>
    """
    return render_page(title, content, show_debug_info=True)

@app.route('/deserialize')
def insecure_deserialization():
    encoded_data = request.args.get('data')
    title = "Load Saved Shopping Cart"
    result_html = ""
    status_code = 200

    if not encoded_data:
        result_html = "<p class='flash error'>Error: No saved cart data provided in 'data' parameter.</p>"
        status_code = 400
    else:
        try:
            pickled_data = base64.urlsafe_b64decode(encoded_data)
            # --- Vulnerable Code ---
            deserialized_object = pickle.loads(pickled_data)
            result_html = f"<h3>Cart Loaded Successfully!</h3><p>Cart Contents:</p><pre>{escape(str(deserialized_object))}</pre><p class='warning'>Warning: Loading cart data this way (using pickle) is insecure and can lead to RCE!</p>"
            # --- End ---
        except Exception as e:
            result_html = f"<p class='flash error'>Error loading cart: {escape(str(e))}</p>"
            status_code = 400 # Treat most errors as bad input for demo

    return render_page(title, result_html, show_debug_info=True), status_code

@app.route('/weak_hash')
def weak_hash():
    data_to_hash = request.args.get('data', 'default_password')
    title = "Password Hash Generator (Demo)"
    # --- Vulnerable Code ---
    hasher = hashlib.md5()
    hasher.update(data_to_hash.encode('utf-8'))
    weak_hash_result = hasher.hexdigest()
    # --- End ---
    content = f"""
    <p>This tool demonstrates hashing using the insecure MD5 algorithm.</p>
    <p>Input String: <code>{escape(data_to_hash)}</code></p>
    <p>Generated MD5 Hash: <code>{escape(weak_hash_result)}</code></p>
    <p class='warning'>MD5 is not suitable for password storage!</p>
    """
    return render_page(title, content, show_debug_info=True)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    title = "Upload Profile Picture"
    upload_form_html = f'''
    <p>Upload a new profile picture. Allowed types: {escape(str(ALLOWED_EXTENSIONS))}.</p>
    <p class="warning">Content is not validated - uploading malicious files is possible!</p>
    <form method=post enctype=multipart/form-data class="card">
      <label for="file">Choose file:</label>
      <input type=file name=file id="file">
      <input type=submit value=Upload class="btn">
    </form>
    <p><small>Files saved to <code>./uploads/</code>. Try accessing via LFI demo.</small></p>
    '''

    messages_html = ""
    # Use session directly to get flashes if available
    if '_flashes' in session:
         flashed_messages = session.pop('_flashes') # Clear after getting
         for category, message in flashed_messages:
             messages_html += f'<div class="flash {category}">{escape(message)}</div>'

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part selected.', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for upload.', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(save_path)
                flash(f'Profile picture "{filename}" uploaded!', 'success')
            except Exception as e:
                 flash(f'Error saving picture: {escape(str(e))}', 'error')
            return redirect(url_for('upload_file')) # Redirect even on error to show flash
        else:
            flash(f'Invalid file type. Allowed: {escape(str(ALLOWED_EXTENSIONS))}', 'error')
            return redirect(request.url)

    # GET request
    return render_page(title, messages_html + upload_form_html, current_page='upload')

if __name__ == '__main__':
    print("Starting Vulnerable Emporium app with UI on http://0.0.0.0:5001") # Changed port
    print("Access the app at http://localhost:5001 or http://<your-ip>:5001")
    print("Explore the UI for ecommerce-themed links to vulnerable endpoints.")
    print("Attack Chains and SAST issues listed on the homepage.")
    app.run(debug=True, host='0.0.0.0', port=5001) # Changed port
