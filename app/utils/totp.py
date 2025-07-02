import pyotp
import qrcode
from io import BytesIO
import base64

def generate_totp_secret():
    return pyotp.random_base32()

def get_totp_uri(secret, username, issuer_name="ICC Visitor Management"):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer_name)

def verify_totp(token, secret):
    totp = pyotp.TOTP(secret)
    return totp.verify(token)

def generate_qr_code_base64(uri):
    qr = qrcode.make(uri)
    buf = BytesIO()
    qr.save(buf, format='PNG')
    img_bytes = buf.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')