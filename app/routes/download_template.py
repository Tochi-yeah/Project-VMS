from flask import Blueprint, send_file
from flask_login import login_required
from openpyxl import Workbook
from io import BytesIO

# Create a new Blueprint for this functionality
bp = Blueprint('download_template', __name__)

@bp.route("/download-bulk-template")
@login_required
def download_bulk_template():
    """
    Generates and serves a pre-formatted XLSX template for bulk visitor uploads.
    """
    # Create an in-memory workbook and select the active worksheet
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Visitor Bulk Upload Template"

    # Define the headers. These must exactly match the column names
    # expected by your upload_csv function in request.py
    headers = ["Name", "Email", "Phone", "Purpose", "Address"]
    sheet.append(headers)

    # Add a sample row to guide the user on the expected format
    sample_data = ["John Doe", "john.doe@example.com", "123-456-7890", "Campus Tour", "123 Main St, Tuy, Batangas"]
    sheet.append(sample_data)

    # Save the workbook to a byte stream in memory
    target = BytesIO()
    workbook.save(target)
    target.seek(0) # Move the cursor to the beginning of the stream

    # Send the in-memory file to the user for download
    return send_file(
        target,
        as_attachment=True,
        download_name='visitor_bulk_upload_template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )