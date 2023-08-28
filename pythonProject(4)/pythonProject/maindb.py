import boto3
from flask import Flask, render_template, request, redirect, url_for, session
import csv
import json

import test

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with your secret key for session management

# Create an S3 client
s3_client = boto3.client('s3', region_name=test.AWS_REGION, aws_access_key_id=test.AWS_ACCESS_KEY, aws_secret_access_key=test.AWS_SECRET_KEY)

# Load user-specific templates from the JSON file (if available)
def load_user_templates():
    try:
        with open('user_templates.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

user_templates = load_user_templates()

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def authenticate():
    # Get the entered username and password from the login form
    username = request.form['username']
    password = request.form['password']

    # Add code here to authenticate the user against Active Directory
    # You can use the ldap3 library to connect to AD and verify the credentials

    # For demonstration purposes, check if the username and password match a user
    if username == 'abhishekdubey@orientindia.net' and password == 'admin':
        session['username'] = username
        save_user_templates()  # Save the default templates to the JSON file
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        # Retrieve the user-specific templates
        templates = user_templates[session['username']]

        # Retrieve the list of objects (folders/files) in the S3 bucket
        response = s3_client.list_objects_v2(Bucket=test.AWS_BUCKET_NAME, Delimiter='/')

        # Extract the folder names from the S3 response
        folders = [common_prefix.get('Prefix') for common_prefix in response.get('CommonPrefixes', [])]

        return render_template('dashboard.html', username=session['username'], folders=folders, templates=templates)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/edit_templates', methods=['GET', 'POST'])
def edit_templates():
    if 'username' in session:
        if request.method == 'POST':
            for folder in user_templates[session['username']]:
                columns = request.form.getlist(f'{folder}_columns[]')
                data_types = request.form.getlist(f'{folder}_types[]')  # Changed variable name
                delete_columns = request.form.getlist(f'delete_{folder}_columns[]')

                updated_template = []
                for column, data_type in zip(columns, data_types):
                    if column.strip() and data_type.strip():
                        updated_template.append({"Column": column, "type": data_type})

                user_templates[session['username']][folder] = updated_template

                if delete_columns:
                    user_templates[session['username']][folder] = [col for col in user_templates[session['username']][folder] if col['Column'] not in delete_columns]

            save_user_templates()

        # Retrieve the user-specific templates
        templates = user_templates[session['username']]
        return render_template('edit_templates.html', templates=templates)
    else:
        return redirect(url_for('login'))

def save_user_templates():
    # Save the user-specific templates to the JSON file
    with open('user_templates.json', 'w') as file:
        json.dump(user_templates, file)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file was selected in the form
    if 'file' not in request.files:
        return redirect(url_for('dashboard'))

    file = request.files['file']
    folder = request.form['folder']

    if file.filename == '':
        return redirect(url_for('dashboard'))

    # Check if the folder is valid and has expected column names
    if folder not in user_templates[session['username']]:
        return "Invalid folder selection"

    expected_columns = user_templates[session['username']][folder]

    # Read the first row (column names) from the CSV file
    csv_file = file.stream.read().decode('utf-8')
    csv_reader = csv.reader(csv_file.splitlines())
    columns = next(csv_reader)

    # Check if all expected columns are present in the uploaded file
    missing_columns = [col for col in expected_columns if col not in columns]
    if missing_columns:
        return f"Columns not found in the file: {', '.join(missing_columns)}"

    # Upload the file to the selected folder in the S3 bucket
    file_key = folder + file.filename
    s3_client.upload_fileobj(file, test.AWS_BUCKET_NAME, file_key)

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
