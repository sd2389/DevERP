# Create a new file: inventory/email_utils.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import io
from django.template.loader import get_template
import logging

logger = logging.getLogger('inventory')

# Check if xhtml2pdf is installed, handle gracefully if not
try:
    from xhtml2pdf import pisa
    XHTML2PDF_INSTALLED = True
except ImportError:
    logger.warning("xhtml2pdf not installed. PDF generation will be disabled.")
    XHTML2PDF_INSTALLED = False

def generate_order_pdf(order_data):
    """
    Generate a PDF file for the order.
    
    Args:
        order_data (dict): Order information including items, customer details, etc.
        
    Returns:
        BytesIO: PDF file as BytesIO object, or None if generation fails
    """
    try:
        # If xhtml2pdf isn't installed, return None
        if not XHTML2PDF_INSTALLED:
            logger.warning("Cannot generate PDF: xhtml2pdf not installed")
            return None
            
        # Get the HTML template
        template = get_template('emails/order_pdf_template.html')
        
        # Render the template with order data
        html = template.render({'order': order_data})
        
        # Create a BytesIO buffer to receive the PDF data
        result = io.BytesIO()
        
        # Generate PDF
        pdf = pisa.pisaDocument(
            io.BytesIO(html.encode("UTF-8")), 
            result,
            encoding='UTF-8'
        )
        
        # Return the PDF file if successful
        if not pdf.err:
            # Reset buffer position to the beginning
            result.seek(0)
            return result
        else:
            logger.error(f"Error generating PDF: {pdf.err}")
            return None
    except Exception as e:
        logger.error(f"Error generating order PDF: {str(e)}")
        return None

def send_order_confirmation_email(order_data, to_email):
    """
    Send order confirmation email with PDF attachment to customer.
    
    Args:
        order_data (dict): Order information including items, customer details, etc.
        to_email (str): Recipient email address
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if email settings are configured
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.warning("Email settings not configured. Skipping email send.")
            return False
            
        # Email subject
        subject = f"Order Confirmation - {order_data['order_id']}"
        
        # Render HTML email content
        html_content = render_to_string(
            'emails/customer_order_confirmation.html', 
            {'order': order_data}
        )
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [to_email]
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        
        # Generate and attach PDF
        pdf_file = generate_order_pdf(order_data)
        if pdf_file:
            email.attach(
                f"Order_{order_data['order_id']}.pdf",
                pdf_file.read(),
                'application/pdf'
            )
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Order confirmation email sent to {to_email} for order {order_data['order_id']}")
        return True
    except Exception as e:
        logger.error(f"Error sending order confirmation email: {str(e)}")
        return False

def send_admin_order_notification(order_data):
    """
    Send order notification email with PDF attachment to admin.
    
    Args:
        order_data (dict): Order information including items, customer details, etc.
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if email settings are configured
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.warning("Email settings not configured. Skipping email send.")
            return False
            
        # Get admin email from settings
        admin_email = getattr(settings, 'ADMIN_ORDER_EMAIL', None)
        
        if not admin_email:
            logger.warning("ADMIN_ORDER_EMAIL not configured. Skipping email send.")
            return False
            
        # Email subject
        subject = f"New Order Received - {order_data['order_id']}"
        
        # Render HTML email content - using admin-specific template
        html_content = render_to_string(
            'emails/admin_order_notification.html', 
            {'order': order_data}
        )
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email]
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        
        # Generate and attach PDF
        pdf_file = generate_order_pdf(order_data)
        if pdf_file:
            email.attach(
                f"Order_{order_data['order_id']}.pdf",
                pdf_file.read(),
                'application/pdf'
            )
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Order notification email sent to admin for order {order_data['order_id']}")
        return True
    except Exception as e:
        logger.error(f"Error sending admin order notification email: {str(e)}")
        return False