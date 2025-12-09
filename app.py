from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-12345')

# In-memory storage only (Vercel compatible)
users = {
    'admin': {
        'password': 'admin123',
        'is_admin': True,
        'is_premium': True,
        'files': ['test.py', 'bot.py'],
        'max_files': 50,
        'is_blocked': False
    }
}

announcements = [{
    'message': 'GOKU FREE HOSTING',
    'author': 'DEV - @gokuuuu_1',
    'timestamp': datetime.now()
}]
processes = {
    'abc123': {
        'filename': 'test.py',
        'username': 'admin',
        'status': 'running',
        'start_time': datetime.now(),
        'cpu': 25,
        'memory': 128
    }
}

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        if not users.get(session['username'], {}).get('is_admin', False):
            flash('Admin access required!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Custom filters FIXED
@app.template_filter('relative_time')
def relative_time_filter(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            return dt
    
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 2592000:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds // 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(seconds // 31536000)
        return f"{years} year{'s' if years > 1 else ''} ago"

@app.template_filter('filesizeformat')
def filesizeformat_filter(bytes):
    try:
        bytes = int(bytes)
    except:
        bytes = 1024
    
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024**2:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024**3:
        return f"{bytes/(1024**2):.1f} MB"
    else:
        return f"{bytes/(1024**3):.1f} GB"

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users.get(username)
        if user and user['password'] == password and not user.get('is_blocked', False):
            session['username'] = username
            session['is_admin'] = user.get('is_admin', False)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        elif user and user.get('is_blocked', False):
            flash('Your account is blocked!', 'error')
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users:
            flash('Username already exists!', 'error')
        elif len(username) < 3:
            flash('Username must be at least 3 characters!', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters!', 'error')
        else:
            users[username] = {
                'password': password,
                'is_admin': False,
                'is_premium': False,
                'files': [],
                'max_files': 10,
                'is_blocked': False
            }
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    username = session['username']
    user = users.get(username, {})
    
    # Mock data for Vercel
    user_files = user.get('files', [])
    user_processes = {pid: p for pid, p in processes.items() if p.get('username') == username}
    
    # File dates
    file_dates = {}
    for f in user_files:
        file_dates[f] = datetime.now()
    
    return render_template('dashboard.html',
                         username=username,
                         is_admin=user.get('is_admin', False),
                         is_premium=user.get('is_premium', False),
                         files=user_files,
                         file_count=len(user_files),
                         max_files=user.get('max_files', 10),
                         processes=user_processes,
                         announcements=announcements[-3:],  # Last 3 announcements
                         system_load=25,
                         storage_used=sum([len(f) * 1024 for f in user_files]),
                         file_sizes={f: len(f) * 1024 for f in user_files},
                         file_dates=file_dates)

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html',
                         users=users,
                         processes=processes)

@app.route('/make_announcement', methods=['POST'])
@admin_required
def make_announcement():
    message = request.form['message']
    if message.strip():
        announcements.append({
            'message': message,
            'author': session['username'],
            'timestamp': datetime.now()
        })
        flash('Announcement posted!', 'success')
    return redirect(url_for('admin'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    username = session['username']
    user = users.get(username, {})
    
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename.endswith('.py'):
            filename = file.filename
            if filename not in user.get('files', []):
                users[username]['files'].append(filename)
                flash('File uploaded successfully!', 'success')
            else:
                flash('File already exists!', 'warning')
        else:
            flash('Only Python (.py) files are allowed', 'error')
    else:
        flash('No file selected', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/start/<filename>')
@login_required
def start_file(filename):
    import uuid
    username = session['username']
    user = users.get(username, {})
    
    if filename in user.get('files', []):
        pid = str(uuid.uuid4())[:8]
        processes[pid] = {
            'filename': filename,
            'username': username,
            'status': 'running',
            'start_time': datetime.now(),
            'cpu': 25,
            'memory': 128
        }
        flash(f'Process {pid} started!', 'success')
    else:
        flash('File not found!', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/stop/<process_id>')
@login_required
def stop_file(process_id):
    if process_id in processes and processes[process_id]['username'] == session['username']:
        processes[process_id]['status'] = 'stopped'
        flash('Process stopped!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete/<filename>')
@login_required
def delete_file(filename):
    username = session['username']
    if filename in users.get(username, {}).get('files', []):
        users[username]['files'].remove(filename)
        
        # Remove related processes
        for pid in list(processes.keys()):
            if processes[pid]['filename'] == filename and processes[pid]['username'] == username:
                del processes[pid]
        
        flash('File deleted!', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/view_logs/<process_id>')
@login_required
def view_logs(process_id):
    process = processes.get(process_id, {})
    logs = f"Process ID: {process_id}\n"
    logs += f"Status: {process.get('status', 'unknown')}\n"
    logs += f"Started: {process.get('start_time', 'N/A')}\n"
    logs += "\n[Simulated logs - Vercel doesn't support actual process execution]\n"
    logs += "2025-12-09 17:30:00 - Process started\n"
    logs += "2025-12-09 17:30:05 - Initializing modules\n"
    logs += "2025-12-09 17:30:10 - Main loop running\n"
    
    return render_template('logs.html',
                         filename=process.get('filename', 'unknown'),
                         status=process.get('status', 'stopped'),
                         logs=logs)

@app.route('/restart_file/<process_id>')
@login_required
def restart_file(process_id):
    if process_id in processes and processes[process_id]['username'] == session['username']:
        processes[process_id]['status'] = 'running'
        processes[process_id]['start_time'] = datetime.now()
        flash('Process restarted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# Remove problematic {% do %} from template
@app.before_request
def fix_templates():
    pass

# Vercel ke liye required
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
