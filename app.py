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
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "expose_headers": ["Content-Disposition"]
        }
    }
)

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
    """Send an email with the requested PDFs to both admin and user"""
    try:
        # Create message for admin
        admin_msg = MIMEMultipart()
        admin_msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        admin_msg['To'] = 'inquiryril@gmail.com'  # Updated to use inquiryril@gmail.com
        admin_msg['Subject'] = f"New PDF Download Request - {form_data.get('firstName', '')} {form_data.get('lastName', '')}"
        
        # Admin email body with all form data
        first_name = form_data.get('firstName', 'Not provided')
        last_name = form_data.get('lastName', '')
        email = form_data.get('email', 'Not provided')
        phone = form_data.get('phone', 'Not provided')
        company = form_data.get('company', 'Not provided')
        category = form_data.get('category', 'Not specified')
        pdf_list = ''.join([f'<li>{pdf}</li>' for pdf in form_data.get('selectedPdfs', [])])
        
        admin_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #e0e0e0; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d; }}
                .info-label {{ font-weight: bold; color: #495057; }}
                .pdf-list {{ background-color: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0; }}
                .pdf-item {{ margin: 5px 0; padding-left: 10px; border-left: 3px solid #007bff; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>New PDF Download Request</h2>
            </div>
            
            <div class="content">
                <p>You have received a new request for PDF downloads with the following details:</p>
                
                <div style="margin: 20px 0;">
                    <p><span class="info-label">Name:</span> {first_name} {last_name}</p>
                    <p><span class="info-label">Email:</span> <a href="mailto:{email}">{email}</a></p>
                    <p><span class="info-label">Phone:</span> <a href="tel:{phone}">{phone}</a></p>
                    <p><span class="info-label">Company:</span> {company}</p>
                    <p><span class="info-label">Category:</span> {category}</p>
                </div>
                
                <div class="pdf-list">
                    <p class="info-label">Requested Documents:</p>
                    {''.join([f'<div class="pdf-item">• {pdf}</div>' for pdf in form_data.get('selectedPdfs', [])])}
                </div>
                
                <p style="margin-top: 20px;">
                    <strong>Next Steps:</strong> Please review this request and follow up with the user if necessary.
                </p>
            </div>
            
            <div class="footer">
                <p>This is an automated notification from Richa Infosystem. Please do not reply to this email.</p>
                <p>© {datetime.datetime.now().year} Richa Infosystem. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        admin_msg.attach(MIMEText(admin_body, 'html'))
        
        # Create message for user
        user_msg = MIMEMultipart()
        user_msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        user_msg['To'] = form_data.get('email')
        user_msg['Subject'] = "Your Requested PDFs from Richa Infosystem"
        
        # User email body
        first_name = form_data.get('firstName', 'Valued Customer')
        pdf_list = ''.join([f'<li>{pdf}</li>' for pdf in form_data.get('selectedPdfs', [])])
        
        user_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #e0e0e0; }}
                .button {{ 
                    display: inline-block; 
                    padding: 10px 20px; 
                    background-color: #28a745; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    margin: 15px 0;
                }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d; }}
                .pdf-list {{ background-color: #f8f9fa; padding: 10px; border-radius: 4px; margin: 15px 0; }}
                .pdf-item {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Thank You for Contacting Richa Infosystem</h2>
            </div>
            
            <div class="content">
                <p>Dear {first_name},</p>
                
                <p>Thank you for your interest in our products/services. We've received your request for the following documents:</p>
                
                <div class="pdf-list">
                    {''.join([f'<div class="pdf-item">• {pdf}</div>' for pdf in form_data.get('selectedPdfs', [])])}
                </div>
                
                <p>Our team is currently processing your request and will get back to you within 24-48 hours.</p>
                
                <p>For your reference, here are the details you provided:</p>
                <p><strong>Email:</strong> {email}<br>
                <strong>Phone:</strong> {phone}</p>
                
                <p>If you have any questions or need immediate assistance, feel free to contact us at <a href="mailto:info@richainfosys.com">info@richainfosys.com</a> or call us at +91-XXXXXXXXXX.</p>
                
                <p>Thank you for choosing Richa Infosystem.</p>
                
                <p>Best regards,<br>
                <strong>The Richa Infosystem Team</strong></p>
            </div>
            
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>© {datetime.datetime.now().year} Richa Infosystem. All rights reserved.</p>
                <p>Our mailing address is:<br>
                Richa Infosystem<br>
                [Your Company Address]<br>
                [City, State, ZIP]</p>
            </div>
        </body>
        </html>
        """
        
        user_msg.attach(MIMEText(user_body, 'html'))
        
        # Connect to SMTP server and send both emails
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            
            # Send admin email
            server.send_message(admin_msg)
            
            # Send user email if email is provided
            if form_data.get('email'):
                server.send_message(user_msg)
            
        return True, None
    except Exception as e:
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
        
        # Validate email format
        user_email = data.get('email', '').strip()
        if user_email and not is_valid_email(user_email):
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address.'
            }), 400
        
        # Validate required fields
        required_fields = ['firstName', 'lastName', 'email', 'phone', 'selectedPdfs', 'category']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Send email with PDF links
        success, error = send_pdf_download_email(data)
        
        if not success:
            return jsonify({
                'success': False,
                'message': f'Failed to send email: {error}'
            }), 500
            
        return jsonify({
            'success': True,
            'message': 'Your PDFs have been sent to your email!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
