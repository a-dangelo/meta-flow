"""
Finance/Expense Tools for Meta-Flow Agents

Mock implementations of expense approval and budget management tools.
All functions use deterministic mock data for POC demo purposes.

POC Limitations:
- No actual database or expense system integration
- Fixed approval thresholds and business rules
- Mock reference number generation (not guaranteed unique)
- Simple business day calculation (weekends only, no holidays)
"""

from typing import Any, Dict
from datetime import datetime, timedelta


def validate_expense_amount(amount: float, **kwargs: Any) -> Dict[str, Any]:
    """
    Validate that expense amount is positive and within policy limits.

    Args:
        amount: Expense amount to validate
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'valid', 'message', and 'details' keys

    POC Note: Uses fixed $10,000 limit. Production would check against
    user role, category-specific limits, and annual spending.
    """
    try:
        # Validation logic
        if not isinstance(amount, (int, float)):
            return {
                'valid': False,
                'message': 'Amount must be a number',
                'details': {'amount': amount, 'type': type(amount).__name__}
            }

        if amount <= 0:
            return {
                'valid': False,
                'message': 'Amount must be greater than zero',
                'details': {'amount': amount}
            }

        # POC policy limit
        MAX_AMOUNT = 10000.00

        if amount > MAX_AMOUNT:
            return {
                'valid': False,
                'message': f'Amount exceeds maximum limit of ${MAX_AMOUNT:,.2f}',
                'details': {'amount': amount, 'limit': MAX_AMOUNT}
            }

        return {
            'valid': True,
            'message': f'Amount ${amount:,.2f} is within policy limits',
            'details': {'amount': amount, 'limit': MAX_AMOUNT}
        }

    except Exception as e:
        return {
            'valid': False,
            'message': f'Validation error: {str(e)}',
            'details': {'error': str(e)}
        }


def check_category_allowed(category: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Check if expense category is allowed under company policy.

    Args:
        category: Expense category name
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'allowed', 'message', and 'details' keys

    POC Note: Uses fixed category list. Production would query policy
    database with user role and department-specific rules.
    """
    # POC allowed categories
    ALLOWED_CATEGORIES = [
        'travel', 'meals', 'office_supplies', 'software', 'hardware',
        'training', 'conference', 'client_entertainment', 'transportation',
        'lodging', 'equipment', 'marketing', 'professional_services'
    ]

    category_lower = category.lower().strip()

    if category_lower in ALLOWED_CATEGORIES:
        return {
            'allowed': True,
            'message': f"Category '{category}' is allowed",
            'details': {'category': category, 'normalized': category_lower}
        }
    else:
        return {
            'allowed': False,
            'message': f"Category '{category}' is not in the approved list",
            'details': {
                'category': category,
                'allowed_categories': ALLOWED_CATEGORIES
            }
        }


def route_for_approval(amount: float, category: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Determine approval routing based on expense amount and category.

    Args:
        amount: Expense amount
        category: Expense category (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'approver', 'level', 'message', and 'details' keys

    POC Note: Uses fixed thresholds. Production would consider:
    - User's reporting hierarchy
    - Department budget authority
    - Category-specific approval chains
    - Delegated approval rules
    """
    try:
        # POC approval thresholds
        if amount < 500:
            approver = 'manager'
            level = 1
            message = 'Direct manager approval required'
        elif amount < 2000:
            approver = 'director'
            level = 2
            message = 'Director approval required'
        elif amount < 5000:
            approver = 'vp'
            level = 3
            message = 'VP approval required'
        else:
            approver = 'cfo'
            level = 4
            message = 'CFO approval required'

        return {
            'approver': approver,
            'level': level,
            'message': message,
            'details': {
                'amount': amount,
                'category': category,
                'threshold_used': 'amount_based'
            }
        }

    except Exception as e:
        return {
            'approver': 'error',
            'level': 0,
            'message': f'Routing error: {str(e)}',
            'details': {'error': str(e)}
        }


def generate_reference_number(prefix: str = 'EXP', **kwargs: Any) -> Dict[str, Any]:
    """
    Generate unique reference number for expense submission.

    Args:
        prefix: Reference number prefix (default: 'EXP')
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'reference_id', 'created_at', and 'expires_at' keys

    POC Note: Uses timestamp-based generation. Production would use:
    - Database sequence or UUID
    - Check for uniqueness
    - Persistent storage
    """
    import random

    now = datetime.now()
    date_part = now.strftime('%Y%m%d')

    # POC: Use random 4-digit suffix (production would use sequence)
    random.seed(now.timestamp())  # Deterministic for same timestamp
    suffix = f"{random.randint(0, 9999):04d}"

    reference_id = f"{prefix}-{date_part}-{suffix}"

    return {
        'reference_id': reference_id,
        'created_at': now.isoformat(),
        'expires_at': None,  # Expense references don't expire
        'prefix': prefix,
        'date_part': date_part,
        'suffix': suffix
    }


def log_expense_submission(
    reference_id: str | None = None,
    amount: float = 0.0,
    category: str | None = None,
    submitter: str = 'user',
    reference_number: Any | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Log expense submission for audit trail.

    Args:
        reference_id: Expense reference number (preferred, may be inferred)
        amount: Expense amount
        category: Expense category
        submitter: User who submitted (default: 'user')
        **kwargs: Additional parameters (e.g., description, date)

    Returns:
        Dict with 'logged', 'timestamp', 'message', and 'details' keys

    POC Note: Returns mock confirmation. Production would:
    - Write to audit database
    - Trigger compliance checks
    - Send notifications
    - Update expense tracking system
    """
    # Ensure we have a reference_id even if the caller used a different name
    if reference_id is None:
        # Common pattern in generated agents: pass a full reference_number dict
        if isinstance(reference_number, dict):
            reference_id = str(
                reference_number.get('reference_id')
                or reference_number.get('id')
                or reference_number.get('value', '')
            )
        elif reference_number is not None:
            reference_id = str(reference_number)
        elif 'reference_id' in kwargs:
            reference_id = str(kwargs['reference_id'])

    if not reference_id:
        raise ValueError("log_expense_submission requires a reference_id")

    # Prefer explicit employee_id if present
    if 'employee_id' in kwargs:
        submitter = str(kwargs['employee_id'])

    timestamp = datetime.now().isoformat()

    return {
        'logged': True,
        'timestamp': timestamp,
        'message': f'Expense {reference_id} logged successfully',
        'details': {
            'reference_id': reference_id,
            'amount': amount,
            'category': category,
            'submitter': submitter,
            'status': 'pending_approval',
            'audit_id': f"AUDIT-{reference_id}"
        }
    }


def calculate_reimbursement_date(submission_date: str = None,
                                 amount: float = 0, **kwargs: Any) -> Dict[str, Any]:
    """
    Calculate expected reimbursement date based on submission date and amount.

    Args:
        submission_date: ISO format date string (default: today)
        amount: Expense amount (affects processing time)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'reimbursement_date', 'business_days', 'message', and 'details' keys

    POC Note: Uses simple business day calculation. Production would:
    - Check approval hierarchy completion
    - Account for payment cycles
    - Consider bank holidays
    - Handle international transfers
    """
    try:
        # Parse submission date or use today
        if submission_date:
            submit_dt = datetime.fromisoformat(submission_date.replace('Z', '+00:00'))
        else:
            submit_dt = datetime.now()

        # POC: Calculate business days based on amount
        if amount < 500:
            business_days = 5
        elif amount < 2000:
            business_days = 7
        else:
            business_days = 10

        # Add business days (skip weekends)
        current_date = submit_dt
        days_added = 0
        while days_added < business_days:
            current_date += timedelta(days=1)
            # Skip weekends (5 = Saturday, 6 = Sunday)
            if current_date.weekday() < 5:
                days_added += 1

        return {
            'reimbursement_date': current_date.strftime('%Y-%m-%d'),
            'business_days': business_days,
            'message': f'Expected reimbursement in {business_days} business days',
            'details': {
                'submission_date': submit_dt.strftime('%Y-%m-%d'),
                'amount': amount,
                'calendar_days': (current_date - submit_dt).days
            }
        }

    except Exception as e:
        return {
            'reimbursement_date': None,
            'business_days': 0,
            'message': f'Calculation error: {str(e)}',
            'details': {'error': str(e)}
        }


def calculate_quarterly_impact(amount: float, category: str,
                              quarter: int = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Calculate impact of expense on quarterly budget.

    Args:
        amount: Expense amount
        category: Expense category
        quarter: Quarter number (1-4, default: current quarter)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'impact', 'budget_remaining', 'percentage_used', and 'details' keys

    POC Note: Uses mock budget data. Production would:
    - Query actual budget allocation database
    - Aggregate YTD spending by category
    - Check against department budgets
    - Provide variance analysis
    """
    # Determine current quarter if not provided
    if quarter is None:
        quarter = (datetime.now().month - 1) // 3 + 1

    # POC: Mock quarterly budgets by category
    QUARTERLY_BUDGETS = {
        'travel': 50000,
        'meals': 10000,
        'office_supplies': 5000,
        'software': 25000,
        'hardware': 30000,
        'training': 15000,
        'conference': 20000,
        'default': 10000
    }

    category_lower = category.lower().strip()
    budget = QUARTERLY_BUDGETS.get(category_lower, QUARTERLY_BUDGETS['default'])

    # POC: Mock current spending (random percentage)
    import random
    random.seed(f"{category_lower}{quarter}")
    current_spending = budget * random.uniform(0.3, 0.7)

    # Calculate impact
    new_total = current_spending + amount
    percentage_used = (new_total / budget) * 100
    remaining = budget - new_total

    return {
        'impact': amount,
        'budget_remaining': max(0, remaining),
        'percentage_used': round(percentage_used, 2),
        'over_budget': new_total > budget,
        'message': f'{percentage_used:.1f}% of Q{quarter} {category} budget used',
        'details': {
            'quarter': quarter,
            'category': category,
            'quarterly_budget': budget,
            'spent_before': round(current_spending, 2),
            'new_total': round(new_total, 2),
            'amount': amount
        }
    }


def set_review_date(submission_date: str = None, priority: str = 'normal',
                   **kwargs: Any) -> Dict[str, Any]:
    """
    Set review date for expense based on priority and submission date.

    Args:
        submission_date: ISO format date string (default: today)
        priority: Priority level ('low', 'normal', 'high', 'urgent')
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'review_date', 'days_until_review', 'message', and 'details' keys

    POC Note: Uses fixed SLAs. Production would:
    - Check reviewer availability
    - Consider approval queue depth
    - Account for business rules
    - Send calendar invites
    """
    try:
        # Parse submission date or use today
        if submission_date:
            submit_dt = datetime.fromisoformat(submission_date.replace('Z', '+00:00'))
        else:
            submit_dt = datetime.now()

        # POC: SLA days based on priority
        priority_sla = {
            'urgent': 1,
            'high': 2,
            'normal': 5,
            'low': 10
        }

        days = priority_sla.get(priority.lower(), 5)

        # Add business days
        current_date = submit_dt
        days_added = 0
        while days_added < days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Skip weekends
                days_added += 1

        return {
            'review_date': current_date.strftime('%Y-%m-%d'),
            'days_until_review': days,
            'message': f'Review scheduled for {current_date.strftime("%Y-%m-%d")}',
            'details': {
                'submission_date': submit_dt.strftime('%Y-%m-%d'),
                'priority': priority,
                'sla_days': days
            }
        }

    except Exception as e:
        return {
            'review_date': None,
            'days_until_review': 0,
            'message': f'Scheduling error: {str(e)}',
            'details': {'error': str(e)}
        }


__all__ = [
    'validate_expense_amount',
    'check_category_allowed',
    'route_for_approval',
    'generate_reference_number',
    'log_expense_submission',
    'calculate_reimbursement_date',
    'calculate_quarterly_impact',
    'set_review_date',
]
