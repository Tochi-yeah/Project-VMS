# app/brevo_mailer.py
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from flask import current_app
from io import BytesIO
import qrcode
import base64

def _get_brevo_api_instance():
    """Configures and returns a Brevo API instance."""
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = current_app.config['BREVO_API_KEY']
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

def send_email(subject, html_content, recipient_email, recipient_name, attachments=None):
    """
    Generic function to send an email using the Brevo API.
    `attachments` should be a list of dicts: [{'name': 'filename.ext', 'content': bytes}]
    """
    api_instance = _get_brevo_api_instance()

    sender = {
        "name": "ICC Visitor Management System",
        "email": "afablejrchito@gmail.com"  # Your verified sender email in Brevo
    }
    to = [{"email": recipient_email, "name": recipient_name}]

    brevo_attachments = []
    if attachments:
        for attachment in attachments:
            encoded_content = base64.b64encode(attachment['content']).decode('utf-8')
            brevo_attachments.append({
                "content": encoded_content,
                "name": attachment['name']
            })

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
        attachment=brevo_attachments if brevo_attachments else None
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        print(f"Exception when calling Brevo API: {e}\n")
        return False

def send_visitor_qr_email(req):
    """Sends a single visitor QR code email."""
    qr_img = qrcode.make(req.unique_code)
    img_io = BytesIO()
    qr_img.save(img_io, format="PNG")
    qr_bytes = img_io.getvalue()

    subject = "Your ICC Visitor QR Code"
    html_content = f"""
    <p>Hello {req.name},</p>
    <p>Your visit request to ICC has been approved.</p>
    <p>Attached is your unique QR code. Use it to check in/out during your visit.</p>
    <p>If you're planning to visit again, please click the link "Already registered?" to change purpose and person to visit.</p>
    <p>Please keep this safe and do not share it with others.</p>
    <br>
    <p>Regards,<br>ICC Visitor Management System</p>
    """
    attachments = [{
        "name": f"qr_{req.unique_code}.png",
        "content": qr_bytes
    }]

    return send_email(subject, html_content, req.email, req.name, attachments)

def send_group_qr_email(reqs):
    """
    Sends group QR (shared code) + each member's own QR in a single email,
    iterating through each member of the group.
    """
    if not reqs:
        return

    group_code = reqs[0].group_code

    # Generate Group QR in memory
    group_qr_img = qrcode.make(group_code)
    group_io = BytesIO()
    group_qr_img.save(group_io, format="PNG")
    group_bytes = group_io.getvalue()

    # Loop through each request in the group
    for r in reqs:
        if not r.email:  # skip if no email for a member
            continue

        # Generate Individual QR in memory
        indiv_qr_img = qrcode.make(r.unique_code)
        indiv_io = BytesIO()
        indiv_qr_img.save(indiv_io, format="PNG")
        indiv_bytes = indiv_io.getvalue()

        # Define email content
        subject = "Your ICC Group & Visitor QR Codes"
        html_content = f"""
        <p>Hello {r.name},</p>
        <p>Your group visit request to ICC has been approved.</p>
        <p>Attached are:</p>
        <ul>
            <li><strong>Individual QR Code:</strong> Use this if you want to check in/out individually.</li>
            <li><strong>Group QR Code:</strong> Use this to check in/out the entire group at once.</li>
        </ul>
        <p>If you plan to visit again, please click the link "Already registered?" to change purpose and person to visit.</p>
        <p>Please keep these QR codes safe and do not share them outside your group.</p>
        <br>
        <p>Regards,<br>ICC Visitor Management System</p>
        """

        attachments = [
            {"name": "Individual-QR.png", "content": indiv_bytes},
            {"name": "Group-QR.png", "content": group_bytes}
        ]

        # Send the email to the current group member
        send_email(subject, html_content, r.email, r.name, attachments)