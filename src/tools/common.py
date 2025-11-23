"""
Common Utility Tools for Meta-Flow Agents

Mock implementations of cross-domain utility tools used across workflows.
All functions use deterministic mock data for POC demo purposes.

POC Limitations:
- No actual notification or messaging system integration
- Mock ID generation (not guaranteed unique across sessions)
- Simple logging (no persistent storage)
- Basic template formatting (no advanced templating engine)
"""

from typing import Any, Dict, List
from datetime import datetime
import re


def send_notification(recipient: str, message: str, channel: str = 'email',
                     priority: str = 'normal', **kwargs: Any) -> Dict[str, Any]:
    """
    Send notification through specified channel.

    Args:
        recipient: Recipient identifier (email, user_id, phone, etc.)
        message: Notification message content
        channel: Notification channel ('email', 'sms', 'slack', 'teams')
        priority: Priority level ('low', 'normal', 'high')
        **kwargs: Additional parameters (e.g., subject, attachments)

    Returns:
        Dict with 'sent', 'notification_id', 'message', and 'details' keys

    POC Note: Returns mock confirmation. Production would:
    - Send actual notifications via respective APIs
    - Handle delivery failures and retries
    - Track delivery status
    - Support templates and personalization
    """
    import random

    timestamp = datetime.now()
    random.seed(f"{recipient}{message}{timestamp.timestamp()}")
    notification_id = f"NOTIF-{random.randint(1000000, 9999999)}"

    # Validate channel
    valid_channels = ['email', 'sms', 'slack', 'teams', 'push']
    channel_lower = channel.lower()

    if channel_lower not in valid_channels:
        return {
            'sent': False,
            'notification_id': None,
            'message': f"Invalid channel: '{channel}'",
            'details': {
                'error': 'invalid_channel',
                'valid_channels': valid_channels
            }
        }

    return {
        'sent': True,
        'notification_id': notification_id,
        'message': f'Notification sent via {channel}',
        'details': {
            'recipient': recipient,
            'channel': channel,
            'priority': priority,
            'sent_at': timestamp.isoformat(),
            'subject': kwargs.get('subject', 'Notification'),
            'delivery_status': 'delivered'
        }
    }


def generate_ticket_id(prefix: str = 'TKT', category: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Generate unique ticket ID for various request types.

    Args:
        prefix: ID prefix (default: 'TKT')
        category: Category for prefix determination (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'ticket_id', 'created_at', and 'details' keys

    POC Note: Uses timestamp-based generation. Production would:
    - Use database sequence or UUID
    - Ensure uniqueness across distributed systems
    - Support custom formatting rules
    - Integrate with tracking systems
    """
    import random

    now = datetime.now()
    date_part = now.strftime('%Y%m%d')

    # Adjust prefix based on category if provided
    if category:
        category_prefixes = {
            'expense': 'EXP',
            'leave': 'LEAVE',
            'hr': 'HR',
            'it': 'IT',
            'hardware': 'HW',
            'software': 'SW'
        }
        prefix = category_prefixes.get(category.lower(), prefix)

    # Generate suffix
    random.seed(now.timestamp())
    suffix = f"{random.randint(0, 9999):04d}"

    ticket_id = f"{prefix}-{date_part}-{suffix}"

    return {
        'ticket_id': ticket_id,
        'created_at': now.isoformat(),
        'details': {
            'prefix': prefix,
            'category': category,
            'date_part': date_part,
            'suffix': suffix,
            'format': 'PREFIX-YYYYMMDD-XXXX'
        }
    }


def log_submission(reference_id: str, submission_type: str, submitter: str,
                  data: Dict = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Log submission for audit trail.

    Args:
        reference_id: Reference ID for submission
        submission_type: Type of submission (expense, leave, ticket, etc.)
        submitter: User who submitted
        data: Additional submission data (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'logged', 'log_id', 'timestamp', 'message', and 'details' keys

    POC Note: Returns mock confirmation. Production would:
    - Write to audit database
    - Support log rotation and archival
    - Enable log queries and analytics
    - Comply with retention policies
    """
    import random

    timestamp = datetime.now()
    random.seed(f"{reference_id}{timestamp.timestamp()}")
    log_id = f"LOG-{random.randint(1000000, 9999999)}"

    return {
        'logged': True,
        'log_id': log_id,
        'timestamp': timestamp.isoformat(),
        'message': f'Submission {reference_id} logged successfully',
        'details': {
            'reference_id': reference_id,
            'submission_type': submission_type,
            'submitter': submitter,
            'data': data or {},
            'status': 'pending',
            'log_level': 'info'
        }
    }


def format_message(template: str, variables: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Format message using template and variables.

    Args:
        template: Message template with {{variable}} placeholders
        variables: Dictionary of variables to substitute
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'formatted', 'message', and 'details' keys

    POC Note: Simple string substitution. Production would:
    - Use proper templating engine (Jinja2, etc.)
    - Support conditional blocks and loops
    - Handle escaping and sanitization
    - Support internationalization
    """
    try:
        # Replace {{variable}} placeholders
        formatted = template
        missing_vars = []

        # Find all {{variable}} patterns
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, template)

        for var_name in matches:
            if var_name in variables:
                # Convert value to string
                value = str(variables[var_name])
                formatted = formatted.replace(f'{{{{{var_name}}}}}', value)
            else:
                missing_vars.append(var_name)

        if missing_vars:
            return {
                'formatted': formatted,
                'message': f'Warning: Missing variables: {", ".join(missing_vars)}',
                'complete': False,
                'details': {
                    'template': template,
                    'missing_variables': missing_vars,
                    'provided_variables': list(variables.keys())
                }
            }

        return {
            'formatted': formatted,
            'message': 'Message formatted successfully',
            'complete': True,
            'details': {
                'template': template,
                'variables_used': list(variables.keys()),
                'character_count': len(formatted)
            }
        }

    except Exception as e:
        return {
            'formatted': template,
            'message': f'Formatting error: {str(e)}',
            'complete': False,
            'details': {'error': str(e)}
        }


def validate_input(value: Any, validation_type: str, constraints: Dict = None,
                  **kwargs: Any) -> Dict[str, Any]:
    """
    Generic input validation function.

    Args:
        value: Value to validate
        validation_type: Type of validation ('email', 'phone', 'date', 'number', 'text')
        constraints: Optional constraints (e.g., min, max, pattern)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'valid', 'message', and 'details' keys

    POC Note: Basic validation rules. Production would:
    - Use comprehensive validation library
    - Support custom validators
    - Provide detailed error messages
    - Handle localized formats
    """
    constraints = constraints or {}

    try:
        if validation_type == 'email':
            # Basic email pattern
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            valid = isinstance(value, str) and re.match(pattern, value) is not None
            message = 'Valid email format' if valid else 'Invalid email format'

        elif validation_type == 'phone':
            # Basic phone pattern (US format)
            pattern = r'^\+?1?\d{10,15}$'
            cleaned = re.sub(r'[^\d+]', '', str(value))
            valid = re.match(pattern, cleaned) is not None
            message = 'Valid phone format' if valid else 'Invalid phone format'

        elif validation_type == 'date':
            # Try parsing as ISO date
            try:
                datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                valid = True
                message = 'Valid date format'
            except ValueError:
                valid = False
                message = 'Invalid date format (expected ISO 8601)'

        elif validation_type == 'number':
            # Numeric validation with optional min/max
            try:
                num = float(value)
                min_val = constraints.get('min')
                max_val = constraints.get('max')

                if min_val is not None and num < min_val:
                    valid = False
                    message = f'Value {num} is below minimum {min_val}'
                elif max_val is not None and num > max_val:
                    valid = False
                    message = f'Value {num} exceeds maximum {max_val}'
                else:
                    valid = True
                    message = 'Valid number'
            except (ValueError, TypeError):
                valid = False
                message = 'Value is not a number'

        elif validation_type == 'text':
            # Text validation with length constraints
            if not isinstance(value, str):
                valid = False
                message = 'Value must be text'
            else:
                min_length = constraints.get('min_length', 0)
                max_length = constraints.get('max_length', float('inf'))
                length = len(value)

                if length < min_length:
                    valid = False
                    message = f'Text too short (min: {min_length}, current: {length})'
                elif length > max_length:
                    valid = False
                    message = f'Text too long (max: {max_length}, current: {length})'
                else:
                    valid = True
                    message = 'Valid text'

        else:
            valid = False
            message = f"Unknown validation type: '{validation_type}'"

        return {
            'valid': valid,
            'message': message,
            'details': {
                'value': value,
                'validation_type': validation_type,
                'constraints': constraints
            }
        }

    except Exception as e:
        return {
            'valid': False,
            'message': f'Validation error: {str(e)}',
            'details': {
                'error': str(e),
                'validation_type': validation_type
            }
        }


__all__ = [
    'send_notification',
    'generate_ticket_id',
    'log_submission',
    'format_message',
    'validate_input',
]
