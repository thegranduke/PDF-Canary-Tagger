from flask import Flask, render_template, request, send_file
import os
import resend
import uuid
import requests
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set the Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

app = Flask(__name__)

# In-memory store mapping PDF ID to metadata
pdf_map = {}

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get('pdf')
    email = request.form.get('email')

    if file and file.filename.endswith('.pdf'):
        # Save uploaded file (optional if you want to archive originals)
        filepath = os.path.join("uploaded_files", file.filename)
        os.makedirs("uploaded_files", exist_ok=True)
        file.save(filepath)

        # Generate a unique ID for this file
        pdf_id = str(uuid.uuid4())

        beacon_url = f"http://127.0.0.1:5000/track.png?id={pdf_id}"

        # Store the association between ID and metadata
        pdf_map[pdf_id] = {
            "email": email,
            "filename": file.filename
        }

        # Generate tagged PDF
        embed_beacon(filepath, beacon_url)

        return send_file(filepath, as_attachment=True)
    return "Invalid file. Please upload a PDF."

@app.route("/track.png")
def track():
    pdf_id = request.args.get("id")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    timestamp = datetime.utcnow().isoformat()
    ua = request.headers.get('User-Agent')
    location = get_location_from_ip(ip)
    print(f"[TRACKED] LOC: {location}, TIME: {timestamp}, UA: {ua}, ID: {pdf_id}")
    
    data = pdf_map.get(pdf_id)
    if data:
        send_tracking_email(ip, timestamp, ua, data["email"],data["filename"],location)
    
    img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))  # Transparent PNG
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


def embed_beacon(filepath, beacon_url):
    # Read the original PDF
    original_pdf = PdfReader(filepath)
    output = PdfWriter()

    # Get the first page
    first_page = original_pdf.pages[0]
    
    # Create a tiny PDF with the beacon
    beacon_buffer = BytesIO()
    c = canvas.Canvas(beacon_buffer)
    
    # Get page dimensions from first page
    page_width = float(first_page.mediabox.width)
    page_height = float(first_page.mediabox.height)
    
    # Place the 1x1 beacon at the bottom-right corner, nearly invisible
    c.drawImage(beacon_url, x=page_width-2, y=1, width=1, height=1, mask='auto')
    c.save()
    beacon_buffer.seek(0)
    
    # Create PDF from the beacon
    beacon_pdf = PdfReader(beacon_buffer)
    beacon_page = beacon_pdf.pages[0]
    
    # Merge the beacon onto the first page
    first_page.merge_page(beacon_page)
    output.add_page(first_page)
    
    # Add all remaining pages unchanged
    for page in original_pdf.pages[1:]:
        output.add_page(page)

    # Write the final PDF
    with open(filepath, "wb") as output_file:
        output.write(output_file)

def send_tracking_email(ip, timestamp, ua, recipient_email,filename,location):
    loc_str = f"{location['city']}, {location['region']}, {location['country']}"
    try:
        email = resend.Emails.send({
            "from": os.getenv("RESEND_EMAIL_FROM"),
            "to": recipient_email,  # Replace with your recipient email
            "subject": "📍 PDF Opened",
            "html": f"""
                <p>Someone opened your tagged PDF filename: {filename}.</p>
                <ul>
                    <li><strong>IP Address:</strong> {ip}</li>
                    <li><strong>Location:</strong> {loc_str}</li>
                    <li><strong>Time:</strong> {timestamp}</li>
                    <li><strong>User Agent:</strong> {ua}</li>
                </ul>
            """
        })
        print("✅ Email sent:", email)
    except Exception as e:
        print("❌ Error sending email:", e)

def get_location_from_ip(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            data = response.json()
            return {
                "city": data.get("city", ""),
                "region": data.get("region", ""),
                "country": data.get("country", "")
            }
    except Exception:
        pass
    return {"city": "", "region": "", "country": ""}

if __name__ == "__main__":
    app.run(debug=True, port=5000)
