from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from werkzeug.utils import secure_filename
from functools import wraps
import datetime
import threading
import time
from config import config

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config.from_object(config[os.getenv('FLASK_ENV', 'development')])

# Enable CORS for all routes
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:5173", 
                "http://127.0.0.1:5173",
                "https://richainfosys.com",
                "https://www.richainfosys.com"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "expose_headers": ["Content-Disposition"]
        }
    }
)

# In-memory tracking to prevent duplicate emails (in production, use Redis or database)
recent_submissions = {}
# Cooldown period in seconds (30 seconds is more user-friendly for testing)
SUBMISSION_COOLDOWN = 30

def create_submission_key(data):
    """Create a unique key for submission tracking"""
    return f"{data.get('email', '').lower()}_{data.get('category', '')}_{len(data.get('selectedPdfs', []))}"

def is_duplicate_submission(data):
    """Check if this is a duplicate submission within cooldown period"""
    key = create_submission_key(data)
    current_time = time.time()
    
    if key in recent_submissions:
        last_submission = recent_submissions[key]
        if current_time - last_submission < SUBMISSION_COOLDOWN:
            return True
    
    # Clean old entries (older than cooldown period)
    keys_to_remove = [k for k, v in recent_submissions.items() if current_time - v > SUBMISSION_COOLDOWN]
    for k in keys_to_remove:
        del recent_submissions[k]
    
    # Record this submission
    recent_submissions[key] = current_time
    return False

def send_contact_email(form_data):
    """Send an email with the contact form data"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = 'info@richainfosys.com'  # Send to company email
        msg['Reply-To'] = form_data.get('email', 'no-reply@richainfosys.com')  # Set reply-to to sender's email
        msg['Subject'] = f"New Contact Form Submission from {form_data.get('name', 'Unknown')}"
        
        # Create HTML version of the message
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">New Contact Form Submission</h2>
                    
                    <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <p><strong>Name:</strong> {form_data.get('name', 'Not provided')}</p>
                        <p><strong>Email:</strong> <a href="mailto:{form_data.get('email', '')}" style="color: #3498db; text-decoration: none;">{form_data.get('email', 'Not provided')}</a></p>
                        <p><strong>Phone:</strong> {form_data.get('phone', 'Not provided')}</p>
                        <p><strong>Subject:</strong> {form_data.get('subject', 'No subject')}</p>
                        <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #3498db;">
                            <p style="margin: 0; font-style: italic;">{form_data.get('message', 'No message provided')}</p>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px; font-size: 12px; color: #7f8c8d; text-align: center;">
                        <p>This email was sent from the contact form on RichaInfosys website.</p>
                        <p> {datetime.datetime.now().year} RichaInfosys. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            
        return True, "Message sent successfully!"
    except Exception as e:
        return False, str(e)

def send_job_application_email(form_data, resume_file=None):
    """Send an email with job application details and resume attachment"""
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = 'hr@richainfosys.com'
        msg['Reply-To'] = form_data.get('email', 'no-reply@richainfosys.com')
        msg['Subject'] = f"New Job Application: {form_data.get('jobTitle', 'No Position Specified')}"
        
        # Create email body
        body = f"""
        <h2>New Job Application Received</h2>
        <p><strong>Position:</strong> {form_data.get('jobTitle', 'Not specified')}</p>
        <p><strong>Name:</strong> {form_data.get('firstName', '')} {form_data.get('lastName', '')}</p>
        <p><strong>Email:</strong> {form_data.get('email', 'Not provided')}</p>
        <p><strong>Phone:</strong> {form_data.get('phone', 'Not provided')}</p>
        <p><strong>Address:</strong> {form_data.get('address', 'Not provided')}</p>
        <p><strong>Applied on:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach resume if provided
        if resume_file and resume_file.filename:
            filename = secure_filename(resume_file.filename)
            attachment = MIMEApplication(
                resume_file.read(),
                Name=filename
            )
            attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            
        return True, "Job application submitted successfully"
    except Exception as e:
        print(f"Error sending job application: {str(e)}")
        return False, str(e)

@app.route('/api/contact', methods=['POST'])
def contact():
    try:
        data = request.get_json()
        
        # Basic validation
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.capitalize()} is required.'
                }), 400
        
        # Send email
        success, message = send_contact_email(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Thank you for your message! We will get back to you soon.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to send message: {message}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.route('/api/apply', methods=['POST'])
def apply_job():
    try:
        # Check if the request has the file part
        if 'resume' not in request.files and 'resume' not in request.form:
            return jsonify({
                'success': False,
                'message': 'No resume file provided'
            }), 400

        # Get form data
        form_data = {
            'firstName': request.form.get('firstName'),
            'lastName': request.form.get('lastName'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'jobTitle': request.form.get('jobTitle')
        }
        
        # Validate required fields
        required_fields = ['firstName', 'lastName', 'email', 'phone', 'jobTitle']
        for field in required_fields:
            if not form_data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.capitalize()} is required.'
                }), 400
        
        # Get resume file if uploaded
        resume_file = request.files.get('resume')
        
        # Validate file type if present
        if resume_file and resume_file.filename != '':
            allowed_extensions = {'pdf', 'doc', 'docx'}
            if '.' not in resume_file.filename or \
               resume_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return jsonify({
                    'success': False,
                    'message': 'Invalid file type. Allowed types: PDF, DOC, DOCX'
                }), 400
        
        # Send job application email with resume
        success, message = send_job_application_email(form_data, resume_file)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Thank you for your application! We will review your details and get back to you soon.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to submit application: {message}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred while processing your application: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'environment': os.getenv('FLASK_ENV', 'development')
    }), 200

def send_pdf_download_email(form_data):
    """Send a single email with the requested PDFs to both admin and user"""
    try:
        # Get form data with fallbacks
        first_name = form_data.get('firstName', 'Not provided')
        last_name = form_data.get('lastName', '')
        email = form_data.get('email', 'Not provided')
        phone = form_data.get('phone', 'Not provided')
        company = form_data.get('organization', 'Not provided')  # Changed from 'company' to 'organization'
        category = form_data.get('category', 'Not specified')
        selected_pdfs = form_data.get('selectedPdfs', [])
        
        # Map PDF values to readable names for email
        pdf_name_mapping = {
            'interactive-panel1': 'Interactive Panel-AI Software',
            'video-conf1': 'Video Conference Systems',
            'digital-signage1': 'Wallmount Digital Signage',
            'digital-signage2': 'Standee Digital Signage',
            'digital-signage3': 'A-Frame Digital Signage',
            'digital-podium1': 'Digital Podium',
            'kiosk1': 'Interactive Kiosk',
            'company-profile1': 'RIL - Company Profile'
        }
        
        # Get readable PDF names
        pdf_names = [pdf_name_mapping.get(pdf, pdf) for pdf in selected_pdfs]
        pdf_list_html = ''.join([f'<li style="margin: 5px 0; padding: 5px 0; border-bottom: 1px solid #eee;">{pdf}</li>' for pdf in pdf_names])
        
        # Create message for admin
        admin_msg = MIMEMultipart()
        admin_msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        admin_msg['To'] = 'inquiryril@gmail.com'
        admin_msg['Subject'] = f"PDF Download Request - {first_name} {last_name}"
        
        # Admin email body
        admin_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; background-color: #f8f9fa; }}
                .container {{ background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 30px; text-align: center; }}
                .header h2 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .content {{ padding: 30px; }}
                .info-section {{ background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; }}
                .info-label {{ font-weight: 600; color: #495057; display: inline-block; min-width: 80px; }}
                .pdf-list {{ background-color: #e3f2fd; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #007bff; }}
                .pdf-list h3 {{ color: #007bff; margin-top: 0; }}
                .pdf-item {{ background-color: white; margin: 8px 0; padding: 10px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6; }}
                .next-steps {{ background-color: #fff3cd; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>📄 New PDF Download Request</h2>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Request received at {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="content">
                    <div class="info-section">
                        <h3 style="color: #007bff; margin-top: 0;">👤 Customer Information</h3>
                        <p><span class="info-label">Name:</span> {first_name} {last_name}</p>
                        <p><span class="info-label">Email:</span> <a href="mailto:{email}" style="color: #007bff; text-decoration: none;">{email}</a></p>
                        <p><span class="info-label">Phone:</span> <a href="tel:{phone}" style="color: #007bff; text-decoration: none;">{phone}</a></p>
                        <p><span class="info-label">Organization:</span> {company}</p>
                        <p><span class="info-label">Category:</span> <span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">{category.replace('-', ' ').title()}</span></p>
                    </div>
                    
                    <div class="pdf-list">
                        <h3>📋 Requested Documents ({len(pdf_names)} items)</h3>
                        <ul style="list-style: none; padding: 0; margin: 10px 0;">
                            {pdf_list_html}
                        </ul>
                    </div>
                    
                    <div class="next-steps">
                        <p style="margin: 0;"><strong>⚡ Action Required:</strong> Please review this request and send the requested PDFs to the customer's email address.</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>Richa Infosystem</strong> - Automated Notification System</p>
                    <p>© {datetime.datetime.now().year} Richa Infosystem. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        admin_msg.attach(MIMEText(admin_body, 'html'))
        
        # Create message for user (acknowledgment)
        user_msg = MIMEMultipart()
        user_msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        user_msg['To'] = email
        user_msg['Subject'] = "Thank you for your interest - Richa Infosystem"
        
        # User email body
        user_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; background-color: #f8f9fa; }}
                .container {{ background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #28a745, #1e7e34); color: white; padding: 30px; text-align: center; }}
                .header h2 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .content {{ padding: 30px; }}
                .pdf-list {{ background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; }}
                .pdf-item {{ background-color: white; margin: 8px 0; padding: 10px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6; }}
                .contact-info {{ background-color: #e3f2fd; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .highlight {{ background-color: #fff3cd; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🙏 Thank You for Your Interest!</h2>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Your request has been successfully received</p>
                </div>
                
                <div class="content">
                    <p>Dear {first_name},</p>
                    
                    <p>Thank you for your interest in our products and services. We have successfully received your request for the following documents:</p>
                    
                    <div class="pdf-list">
                        <h3 style="color: #007bff; margin-top: 0;">📋 Your Requested Documents:</h3>
                        <ul style="list-style: none; padding: 0; margin: 10px 0;">
                            {pdf_list_html}
                        </ul>
                    </div>
                    
                    <div class="highlight">
                        <p style="margin: 0;"><strong>📧 What's Next?</strong> Our team will review your request and send the requested PDFs to your email address within 24-48 hours.</p>
                    </div>
                    
                    <div class="contact-info">
                        <h3 style="color: #007bff; margin-top: 0;">📞 Need Immediate Assistance?</h3>
                        <p style="margin: 5px 0;">Email: <a href="mailto:info@richainfosys.com" style="color: #007bff; text-decoration: none;">info@richainfosys.com</a></p>
                        <p style="margin: 5px 0;">Phone: +91-XXXXXXXXXX</p>
                    </div>
                    
                    <p>We appreciate your interest in Richa Infosystem and look forward to serving you.</p>
                    
                    <p style="margin-top: 25px;">
                        Best regards,<br>
                        <strong style="color: #007bff;">The Richa Infosystem Team</strong>
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>Richa Infosystem</strong> - Your Technology Partner</p>
                    <p>© {datetime.datetime.now().year} Richa Infosystem. All rights reserved.</p>
                    <p style="margin-top: 10px; font-size: 11px;">
                        This is an automated message. Please do not reply to this email.<br>
                        If you have questions, contact us at info@richainfosys.com
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        user_msg.attach(MIMEText(user_body, 'html'))
        
        # Send emails using a single SMTP connection
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            
            # Send admin email
            server.send_message(admin_msg)
            print(f"Admin email sent successfully for {first_name} {last_name}")
            
            # Send user email if email is provided
            if email and email.strip():
                server.send_message(user_msg)
                print(f"User acknowledgment email sent to {email}")
            
        return True, None
        
    except Exception as e:
        print(f"Error in send_pdf_download_email: {str(e)}")
        return False, str(e)

def is_valid_email(email):
    """Basic email validation"""
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return False
    return True

@app.route('/api/downloads/request', methods=['POST'])
def request_downloads():
    try:
        data = request.get_json()
        
        # Check for duplicate submission
        if is_duplicate_submission(data):
            return jsonify({
                'success': False,
                'message': 'Request already submitted recently. Please wait before submitting again.'
            }), 429
        
        # Validate email format
        user_email = data.get('email', '').strip()
        if not user_email or not is_valid_email(user_email):
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address.'
            }), 400
        
        # Validate required fields
        required_fields = ['firstName', 'lastName', 'email', 'phone', 'selectedPdfs', 'category']
        missing_fields = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate selectedPdfs is not empty
        if not isinstance(data.get('selectedPdfs'), list) or len(data.get('selectedPdfs', [])) == 0:
            return jsonify({
                'success': False,
                'message': 'Please select at least one PDF document.'
            }), 400
        
        # Send email with PDF information
        success, error = send_pdf_download_email(data)
        
        if not success:
            print(f"Failed to send PDF download email: {error}")
            return jsonify({
                'success': False,
                'message': f'Failed to process your request: {error}'
            }), 500
            
        return jsonify({
            'success': True,
            'message': 'Thank you! Your request has been received and will be processed shortly.'
        })
        
    except Exception as e:
        print(f"Error in request_downloads: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])