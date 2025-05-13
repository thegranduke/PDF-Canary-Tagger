from flask import Flask, render_template, request
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get('pdf')
    if file and file.filename.endswith('.pdf'):
        filepath = os.path.join("uploaded_files", file.filename)
        file.save(filepath)
        return f"Uploaded: {file.filename}"
    return "Invalid file. Please upload a PDF."

if __name__ == '__main__':
    app.run(debug=True)