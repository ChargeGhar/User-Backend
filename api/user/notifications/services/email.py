from __future__ import annotations

import logging
from typing import Dict, Any, List

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from api.common.services.base import BaseService, ServiceException
logger = logging.getLogger(__name__)

class EmailService(BaseService):
    """Service for sending emails"""

    def __init__(self):
        super().__init__()
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def send_email(
        self,
        subject: str,
        recipient_list: List[str],
        template_name: str,
        context: Dict[str, Any],
    ):
        """
        Send email using an HTML template.

        Args:
            subject (str): Email subject.
            recipient_list (List[str]): List of recipient email addresses.
            template_name (str): The filename of the email template.
            context (Dict[str, Any]): A dictionary of context variables for the template.
        """
        if not recipient_list:
            logger.warning("Recipient list is empty. No email sent.")
            return

        try:
            logger.info(f"Attempting to send email with subject '{subject}' to {recipient_list}")

            # Render HTML content from template
            html_content = render_to_string(template_name, context)

            # Create the email message
            email = EmailMultiAlternatives(
                subject=subject,
                body="",  # Plain text body is empty, we use HTML
                from_email=self.from_email,
                to=recipient_list,
            )
            email.attach_alternative(html_content, "text/html")

            # Send the email
            sent_count = email.send()

            if sent_count > 0:
                logger.info(f"Successfully sent email to {recipient_list}")
            else:
                logger.error(f"Failed to send email to {recipient_list}. The send() method returned 0.")
                raise ServiceException("Failed to send email")

        except Exception as e:
            logger.critical(
                f"A critical error occurred while sending an email to {recipient_list}. Error: {str(e)}",
                exc_info=True,
            )
            self.handle_service_error(e, "Failed to send email")