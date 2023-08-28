import boto3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your secret key for session management

# AWS credentials
AWS_ACCESS_KEY = 'AKIAQUBRCP2YEXVTGOFQ'  # Replace with your AWS access key
AWS_SECRET_KEY = 'gzv/hN7NQJ833hIu0W5vxSmG/j6bEegmbSYXAzam'  # Replace with your AWS secret key
AWS_BUCKET_NAME = 'reporting-app-bucket'
AWS_REGION = 'ap-south-1'

# Create an S3 client with IAM role credentials
s3_client = boto3.client('s3', region_name=AWS_REGION)


@app.route('/')
def login():
    return render_template('login.html')


@app.route('/auth', methods=['POST'])
def authenticate():
    # Get the entered username and password from the login form
    username = request.form['username']
    password = request.form['password']

    # For demonstration purposes, check if the username and password are 'admin'
    if username == 'abhishekdubey@orientindia.net' and password == 'admin':
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        # List all the folders in the bucket and pass them to the dashboard template
        response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME, Delimiter='/')
        folders = [common_prefix['Prefix'].split('/')[0] for common_prefix in response.get('CommonPrefixes', [])]
        return render_template('dashboard.html', username=session['username'], folders=folders)
    else:
        return redirect(url_for('login'))


@app.route('/upload', methods=['POST'])
def upload():
    if 'username' in session:
        folder_name = request.form['folder']
        file = request.files['file']
        if file:
            file_key = folder_name + '/' + file.filename
            # Generate a pre-signed URL for file upload with 5-minute expiration time
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': AWS_BUCKET_NAME, 'Key': file_key},
                ExpiresIn=300
            )
            # Redirect the user to the pre-signed URL to complete the upload
            return redirect(presigned_url)

    return redirect(url_for('dashboard'))


@app.route('/download', methods=['POST'])
def download():
    if 'username' in session:
        folder_name = request.form['folder']
        file_name = request.form['file']
        file_key = folder_name + '/' + file_name
        # Generate a pre-signed URL for file download with 5-minute expiration time
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': AWS_BUCKET_NAME, 'Key': file_key},
            ExpiresIn=300
        )
        # Redirect the user to the pre-signed URL to initiate the download
        return redirect(presigned_url)

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
