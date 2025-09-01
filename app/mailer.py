from flask_mail import Message
from io import BytesIO
import qrcode
from app import mail
import os

def send_visitor_qr_email(req):
    qr_data = req.unique_code

    # Generate QR in memory
    qr_img = qrcode.make(qr_data)
    img_io = BytesIO()
    qr_img.save(img_io, format="PNG")
    img_io.seek(0)

    msg = Message("Your ICC Visitor QR Code", recipients=[req.email])
    msg.body = f"""Hello {req.name},

Your visit request to ICC has been approved.

Attached is your unique QR code.
Use it to check in/out during your visit.

If you're planning to visit again, please click the link "Already registered?"
to change purpose and person to visit.

Please keep this safe and do not share it with others.

Regards,
ICC Visitor Management System
"""

    msg.attach(f"qr_{req.unique_code}.png", "image/png", img_io.read())
    mail.send(msg)

def send_email(to, subject, body, attachments=None):
    msg = Message(subject, recipients=[to], body=body)
    if attachments:
        for path in attachments:
            with open(path, 'rb') as f:
                msg.attach(filename=path.split('/')[-1], content_type='image/png', data=f.read())
    mail.send(msg)

def send_group_qr_email(reqs):
    """
    Send group QR (shared code) + each member's own QR in a single email.
    reqs = list of Request objects (all belonging to same group_code).
    """

    if not reqs:
        return

    group_code = reqs[0].group_code

    # Generate Group QR in memory
    group_qr_img = qrcode.make(group_code)
    group_io = BytesIO()
    group_qr_img.save(group_io, format="PNG")
    group_io.seek(0)
    group_bytes = group_io.read()

    for r in reqs:
        if not r.email:  # skip if no email
            continue

        # Individual QR
        indiv_qr_img = qrcode.make(r.unique_code)
        indiv_io = BytesIO()
        indiv_qr_img.save(indiv_io, format="PNG")
        indiv_io.seek(0)
        indiv_bytes = indiv_io.read()

        msg = Message("Your ICC Group & Visitor QR Codes", recipients=[r.email])
        msg.body = f"""Hello {r.name},

Your group visit request to ICC has been approved.

Attached are:
 Individual QR Code — use this if you want to check in/out individually.  

 Group QR Code — use this to check in/out the entire group at once.  

If you plan to visit again please click the link "Already registered?" 
to change purpose and person to visit.

Please keep these QR codes safe and do not share outside your group.

Regards,  
ICC Visitor Management System
"""

        msg.attach("Individual-QR.png", "image/png", indiv_bytes)
        msg.attach("Group-QR.png", "image/png", group_bytes)

        mail.send(msg)
