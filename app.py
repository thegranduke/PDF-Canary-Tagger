from flask import Flask, render_template, request, send_file
import os
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from PIL import Image

app = Flask(__name__)

# Beacon URL
BEACON_URL = "http://127.0.0.1:5000/track.png"

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get('pdf')
    if file and file.filename.endswith('.pdf'):
        # Save uploaded file (optional if you want to archive originals)
        filepath = os.path.join("uploaded_files", file.filename)
        os.makedirs("uploaded_files", exist_ok=True)
        file.save(filepath)

        # Generate tagged PDF
        embed_beacon(filepath, BEACON_URL)

        return send_file(filepath, as_attachment=True)
    return "Invalid file. Please upload a PDF."

@app.route("/track.png")
def track():
    ip = request.remote_addr
    timestamp = datetime.utcnow().isoformat()
    ua = request.headers.get('User-Agent')
    print(f"[TRACKED] IP: {ip}, TIME: {timestamp}, UA: {ua}")
    img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))  # Transparent PNG
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


def embed_beacon(filepath, beacon_url):
    buffer = BytesIO()
    c = canvas.Canvas(buffer)

    # Draw the beacon image (loads remotely on PDF open)
    c.drawImage(beacon_url, x=0, y=0, width=1, height=1, mask='auto')

    # c.drawString(100, 750, "This PDF is tagged with a beacon.")

    c.save()
    with open(filepath, "wb") as f:
        f.write(buffer.getvalue())

if __name__ == "__main__":
    app.run(debug=True, port=5000)
