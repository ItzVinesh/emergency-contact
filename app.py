from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
import csv
import os
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = 'secret_key'  # Change this in production

# CSV file path
CSV_FILE = os.path.join(app.root_path, 'users.csv')
CSV_FIELDS = ['username', 'name', 'aadhaar_no', 'medical_emergency', 'password_hash', 'last_login']

DEMO_USERS = {
    'admin': {
        'password': '123',
        'name': 'Admin User',
        'aadhaar_no': '123456789012',
        'medical_emergency': 'Emergency Contact: ABC, Phone: 9876543210'
    },
    'manager': {
        'password': 'manager123',
        'name': 'Manager User',
        'aadhaar_no': '234567890123',
        'medical_emergency': 'Emergency Contact: XYZ, Phone: 9123456780'
    },
    'staff': {
        'password': 'staff123',
        'name': 'Staff User',
        'aadhaar_no': '345678901234',
        'medical_emergency': 'Emergency Contact: PQR, Phone: 9988776655'
    }
}

def init_csv():
    """
    Initializes the CSV and keeps the demo record available for searches.
    """
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

    existing_usernames = {row.get('username') for row in rows}
    added_user = False
    for username, profile in DEMO_USERS.items():
        if username not in existing_usernames:
            added_user = True
            rows.append({
                'username': username,
                'name': profile['name'],
                'aadhaar_no': profile['aadhaar_no'],
                'medical_emergency': profile['medical_emergency'],
                'password_hash': generate_password_hash(profile['password']),
                'last_login': ''
            })

    # Rewrite when upgrading an older CSV so its new columns are available.
    if not os.path.exists(CSV_FILE) or added_user or rows and set(rows[0]) != set(CSV_FIELDS):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows({field: row.get(field, '') for field in CSV_FIELDS} for row in rows)

init_csv()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin-data')
def admin_data():
    """Show the latest non-sensitive records from the CSV."""
    with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    public_rows = [
        {
            'username': row.get('username', ''),
            'name': row.get('name', ''),
            'aadhaar_no': row.get('aadhaar_no', ''),
            'medical_emergency': row.get('medical_emergency', ''),
            'last_login': row.get('last_login', '') or 'Not logged in'
        }
        for row in rows
    ]
    return render_template('admin_data.html', rows=public_rows)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        account = DEMO_USERS.get(username)

        # For production, credentials should be stored in a database.
        if account and password == account['password']:
            # Store user info in session.
            session['username'] = username
            session['user'] = {
                'username': username,
                'name': account['name'],
                'aadhaar_no': account['aadhaar_no'],
                'medical_emergency': account['medical_emergency']
            }

            # Update the admin profile and latest login time in the CSV.
            rows = []
            with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            login_time = datetime.now(timezone.utc).isoformat(timespec='seconds')
            saved = False
            for row in rows:
                if row.get('username') == username:
                    row.update({
                        'username': username,
                        'name': account['name'],
                        'aadhaar_no': account['aadhaar_no'],
                        'medical_emergency': account['medical_emergency']
                    })
                    row['password_hash'] = generate_password_hash(password)
                    row['last_login'] = login_time
                    saved = True
                    break

            if not saved:
                new_user = {
                    'username': username,
                    'name': account['name'],
                    'aadhaar_no': account['aadhaar_no'],
                    'medical_emergency': account['medical_emergency']
                }
                new_user['password_hash'] = generate_password_hash(password)
                new_user['last_login'] = login_time
                rows.append(new_user)

            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

            # Redirect to search page
            return redirect(url_for('search'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    # Check if user is logged in
    if 'username' not in session:
        # Redirect to login page if not logged in
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Search by Aadhaar No
        aadhaar_no = request.form.get('aadhaar_no')

        # Read CSV and search for Aadhaar No
        user_info = None
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['aadhaar_no'].strip() == aadhaar_no.strip():
                    user_info = row
                    break

        if user_info:
            return render_template('search_results.html', user=user_info)
        else:
            return render_template('search_results.html', error='User not found.')

    # For GET request, display a form to search
    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True)
