from flask import Flask, request, render_template, redirect, url_for, send_file, flash
import pandas as pd
import os
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)  # Create the Flask app instance
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder where files will be saved
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Create uploads folder if it doesn't exist
app.secret_key = 'supersecretkey'  # Secret key for sessions (flash messages)

# Allowed file extensions (only CSV allowed)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash('File successfully uploaded! Starting data cleaning process...')
            return redirect(url_for('clean_data', filename=filename))
        else:
            flash('Invalid file format. Please upload a CSV file.')
            return redirect(request.url)
    return render_template('upload.html')  # Render upload.html when GET request

@app.route('/clean/<filename>')
def clean_data(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        df = pd.read_csv(filepath)  # Read the uploaded CSV file
    except Exception as e:
        flash(f'Error reading CSV file: {e}')
        return redirect(url_for('upload_file'))  # Redirect back if there's an error

    # Basic data cleaning
    df.drop_duplicates(inplace=True)  # Drop duplicate rows
    df.fillna(method='ffill', inplace=True)  # Fill missing values with forward fill

    # Convert date columns (if any)
    for col in df.columns:
        if 'date' in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Handling outliers by replacing extreme values with NaN
    for col in df.select_dtypes(include=[np.number]).columns:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        df[col] = np.where((df[col] < lower_bound) | (df[col] > upper_bound), np.nan, df[col])
    df.fillna(method='ffill', inplace=True)  # Fill NaN values after outlier treatment

    # Standardizing text columns (strip and lowercase)
    for col in df.select_dtypes(include=[object]).columns:
        df[col] = df[col].str.strip().str.lower()

    # Summary statistics for cleaned data
    summary = df.describe().to_html()  # Generate HTML table of summary stats

    # Save the cleaned file
    cleaned_filename = 'cleaned_' + filename
    cleaned_filepath = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
    df.to_csv(cleaned_filepath, index=False)

    flash(f'File "{filename}" successfully cleaned!')

    # Render result page and pass the summary and cleaned file link
    return render_template('result.html', summary=summary, cleaned_filename=cleaned_filename)

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(filepath, as_attachment=True)  # Allow users to download the cleaned file

if __name__ == '__main__':
    app.run(debug=True)  # Run the app in debug mode
