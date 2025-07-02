# app/mailer.py
from flask_mail import Message
from io import BytesIO
import qrcode
from app import mail

def send_visitor_qr_email(req):
    qr_data = req.unique_code
    qr = qrcode.make(qr_data)

    qr_io = BytesIO()
    qr.save(qr_io, format='PNG')
    qr_io.seek(0)

    msg = Message("Your ICC Visitor QR Code", recipients=[req.email])
    msg.body = f"""Hello {req.name},

Your visit request to ICC has been approved.

Attached is your unique QR code.
Use it to check in/out during your visit.

Regards,
ICC Visitor Management System"""
    msg.attach("visitor_qr.png", "image/png", qr_io.read())
    mail.send(msg)
