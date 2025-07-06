from flask_mail import Message
from io import BytesIO
import qrcode
from app import mail
import os

def send_visitor_qr_email(req):
    qr_data = req.unique_code
    qr = qrcode.make(qr_data)

    # Set the directory path
    temp_dir = os.path.join(os.getcwd(), 'app', 'static', 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    # Generate unique file name
    file_name = f"qr_{req.unique_code}.png"
    file_path = os.path.join(temp_dir, file_name)

    # Save QR to file path
    qr.save(file_path)

    # Load image bytes for attachment
    with open(file_path, 'rb') as f:
        qr_bytes = f.read()

    msg = Message("Your ICC Visitor QR Code", recipients=[req.email])
    msg.body = f"""Hello {req.name},

Your visit request to ICC has been approved.

Attached is your unique QR code.
Use it to check in/out during your visit.

If your planning to visit again please click the link "already registered?"
to change purpose and person to visit.

Please keep this safe and do not share it with others.


Regards,
ICC Visitor Management System"""

    msg.attach(file_name, "image/png", qr_bytes)
    mail.send(msg)
