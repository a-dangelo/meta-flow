"""
HR Tools for Meta-Flow Agents

Mock implementations of HR, leave management, and onboarding tools.
All functions use deterministic mock data for POC demo purposes.

POC Limitations:
- No actual HRIS or leave management system integration
- Fixed leave balances and approval rules
- Mock employee data (not real employee records)
- Simple conflict detection (no calendar integration)
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta


def calculate_total_days(start_date: str, end_date: str,
                        include_half_days: bool = False, **kwargs: Any) -> Dict[str, Any]:
    """
    Calculate total days between start and end dates, optionally handling half-days.

    Args:
        start_date: ISO format start date
        end_date: ISO format end date
        include_half_days: Whether to count half-days (0.5 increments)
        **kwargs: May include 'half_day_dates' list

    Returns:
        Dict with 'total_days', 'business_days', 'message', and 'details' keys

    POC Note: Simple day calculation. Production would:
    - Check company holiday calendar
    - Handle different time zones
    - Support partial day increments
    - Integrate with leave policy rules
    """
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Calculate calendar days (inclusive)
        calendar_days = (end_dt - start_dt).days + 1

        # Calculate business days (skip weekends)
        business_days = 0
        current = start_dt
        while current <= end_dt:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1
            current += timedelta(days=1)

        # Handle half-days if specified
        half_day_dates = kwargs.get('half_day_dates', [])
        half_day_adjustment = len(half_day_dates) * 0.5 if include_half_days else 0

        total_days = business_days - half_day_adjustment

        return {
            'total_days': total_days,
            'business_days': business_days,
            'calendar_days': calendar_days,
            'half_day_adjustment': half_day_adjustment,
            'message': f'Total: {total_days} days ({business_days} business days)',
            'details': {
                'start_date': start_date,
                'end_date': end_date,
                'weekend_days': calendar_days - business_days,
                'half_day_dates': half_day_dates
            }
        }

    except Exception as e:
        return {
            'total_days': 0,
            'business_days': 0,
            'calendar_days': 0,
            'message': f'Calculation error: {str(e)}',
            'details': {'error': str(e)}
        }


def check_leave_balance(employee_id: str, leave_type: str = 'vacation',
                       days_requested: float = 0, **kwargs: Any) -> Dict[str, Any]:
    """
    Check employee's leave balance for requested leave type.

    Args:
        employee_id: Employee identifier
        leave_type: Type of leave ('vacation', 'sick', 'personal')
        days_requested: Number of days requested
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'available', 'balance', 'sufficient', 'message', and 'details' keys

    POC Note: Returns mock balances. Production would:
    - Query HRIS database for actual balances
    - Check accrual rates and carry-over rules
    - Consider pending/approved requests
    - Handle different leave policies by region
    """
    # POC: Mock leave balances (all employees get same balance)
    MOCK_BALANCES = {
        'vacation': 15.0,
        'sick': 10.0,
        'personal': 5.0,
    }

    leave_type_lower = leave_type.lower()
    balance = MOCK_BALANCES.get(leave_type_lower, 0.0)
    sufficient = days_requested <= balance

    return {
        'available': balance > 0,
        'balance': balance,
        'sufficient': sufficient,
        'remaining': max(0, balance - days_requested),
        'message': f'{balance} {leave_type} days available' + (
            f', sufficient for {days_requested} days' if sufficient else
            f', insufficient for {days_requested} days'
        ),
        'details': {
            'employee_id': employee_id,
            'leave_type': leave_type,
            'days_requested': days_requested,
            'balance_source': 'mock_data'
        }
    }


def check_team_conflicts(start_date: str, end_date: str, team_id: str = None,
                        employee_id: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Check for conflicting leave requests within the same team.

    Args:
        start_date: ISO format start date
        end_date: ISO format end date
        team_id: Team identifier (optional)
        employee_id: Employee identifier (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'conflicts', 'conflict_count', 'message', and 'details' keys

    POC Note: Returns mock conflicts. Production would:
    - Query approved/pending leave requests
    - Check team minimum coverage requirements
    - Consider critical roles and backups
    - Integrate with project deadlines
    """
    import random

    # POC: Randomly determine if there are conflicts (deterministic based on dates)
    random.seed(f"{start_date}{end_date}{team_id}")
    has_conflicts = random.random() < 0.3  # 30% chance of conflicts

    if has_conflicts:
        # Generate mock conflicting employees
        conflict_count = random.randint(1, 3)
        conflicting_employees = [
            {
                'employee_id': f'EMP-{random.randint(100000, 999999)}',
                'name': f'Employee {i+1}',
                'dates': f'{start_date} to {end_date}',
                'status': random.choice(['approved', 'pending'])
            }
            for i in range(conflict_count)
        ]

        return {
            'conflicts': True,
            'conflict_count': conflict_count,
            'message': f'{conflict_count} team member(s) have overlapping leave',
            'details': {
                'start_date': start_date,
                'end_date': end_date,
                'team_id': team_id,
                'conflicting_employees': conflicting_employees
            }
        }
    else:
        return {
            'conflicts': False,
            'conflict_count': 0,
            'message': 'No team conflicts found',
            'details': {
                'start_date': start_date,
                'end_date': end_date,
                'team_id': team_id,
                'checked': True
            }
        }


def verify_deadlines(start_date: str, end_date: str, employee_id: str = None,
                    **kwargs: Any) -> Dict[str, Any]:
    """
    Verify if employee has critical deadlines during requested leave period.

    Args:
        start_date: ISO format start date
        end_date: ISO format end date
        employee_id: Employee identifier (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'has_deadlines', 'deadline_count', 'message', and 'details' keys

    POC Note: Returns mock deadlines. Production would:
    - Query project management systems
    - Check deliverable due dates
    - Consider milestone dependencies
    - Integrate with task assignments
    """
    import random

    # POC: Randomly determine if there are deadlines
    random.seed(f"{employee_id}{start_date}{end_date}")
    has_deadlines = random.random() < 0.25  # 25% chance of deadlines

    if has_deadlines:
        deadline_count = random.randint(1, 2)
        deadlines = [
            {
                'project': f'Project {chr(65+i)}',
                'deadline': start_date,  # Simplified
                'criticality': random.choice(['high', 'medium']),
                'description': f'Deliverable due during leave period'
            }
            for i in range(deadline_count)
        ]

        return {
            'has_deadlines': True,
            'deadline_count': deadline_count,
            'critical': any(d['criticality'] == 'high' for d in deadlines),
            'message': f'{deadline_count} critical deadline(s) during leave period',
            'details': {
                'start_date': start_date,
                'end_date': end_date,
                'employee_id': employee_id,
                'deadlines': deadlines
            }
        }
    else:
        return {
            'has_deadlines': False,
            'deadline_count': 0,
            'critical': False,
            'message': 'No critical deadlines during leave period',
            'details': {
                'start_date': start_date,
                'end_date': end_date,
                'employee_id': employee_id
            }
        }


def route_leave_approval(days_requested: float, leave_type: str,
                        employee_id: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Determine approval routing for leave request based on duration and type.

    Args:
        days_requested: Number of days requested
        leave_type: Type of leave
        employee_id: Employee identifier (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'approver', 'level', 'message', and 'details' keys

    POC Note: Uses fixed routing rules. Production would:
    - Query organizational hierarchy
    - Check delegated approvers
    - Consider leave type policies
    - Handle multi-level approvals
    """
    # POC: Route based on duration
    if days_requested <= 3:
        approver = 'manager'
        level = 1
        auto_approve = False
    elif days_requested <= 10:
        approver = 'manager'
        level = 1
        auto_approve = False
    else:
        approver = 'hr_director'
        level = 2
        auto_approve = False

    # Extended leave requires HR review
    if days_requested > 15:
        approver = 'hr_director'
        level = 2
        message = 'Extended leave requires HR Director approval'
    else:
        message = f'{approver} approval required'

    return {
        'approver': approver,
        'level': level,
        'auto_approve': auto_approve,
        'message': message,
        'details': {
            'days_requested': days_requested,
            'leave_type': leave_type,
            'employee_id': employee_id,
            'routing_rule': 'duration_based'
        }
    }


def update_team_calendar(employee_id: str, start_date: str, end_date: str,
                        leave_type: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Update team calendar with approved leave.

    Args:
        employee_id: Employee identifier
        start_date: ISO format start date
        end_date: ISO format end date
        leave_type: Type of leave
        **kwargs: Additional parameters (e.g., team_id)

    Returns:
        Dict with 'updated', 'calendar_event_id', 'message', and 'details' keys

    POC Note: Returns mock confirmation. Production would:
    - Create calendar events in Outlook/Google Calendar
    - Update team availability views
    - Send calendar invites
    - Sync with project planning tools
    """
    import random

    # Generate mock calendar event ID
    random.seed(f"{employee_id}{start_date}{end_date}")
    event_id = f"CAL-{random.randint(100000, 999999)}"

    return {
        'updated': True,
        'calendar_event_id': event_id,
        'message': f'Team calendar updated for {employee_id}',
        'details': {
            'employee_id': employee_id,
            'start_date': start_date,
            'end_date': end_date,
            'leave_type': leave_type,
            'team_id': kwargs.get('team_id', 'unknown'),
            'visibility': 'team'
        }
    }


def send_confirmation_email(employee_id: str, request_type: str,
                           status: str, details: Dict = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Send confirmation email for HR request.

    Args:
        employee_id: Employee identifier
        request_type: Type of request (leave, complaint, etc.)
        status: Request status (approved, pending, etc.)
        details: Additional details to include in email
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'sent', 'message_id', 'message', and 'details' keys

    POC Note: Returns mock confirmation. Production would:
    - Send actual emails via SMTP/SendGrid
    - Use HTML templates
    - Include actionable links
    - Track delivery status
    """
    import random

    timestamp = datetime.now()
    random.seed(f"{employee_id}{request_type}{timestamp.timestamp()}")
    message_id = f"MSG-{random.randint(1000000, 9999999)}"

    return {
        'sent': True,
        'message_id': message_id,
        'message': f'Confirmation email sent to {employee_id}',
        'details': {
            'employee_id': employee_id,
            'request_type': request_type,
            'status': status,
            'sent_at': timestamp.isoformat(),
            'subject': f'{request_type.title()} Request - {status.title()}',
            'additional_details': details or {}
        }
    }


def generate_case_number(case_type: str = 'HR', **kwargs: Any) -> Dict[str, Any]:
    """
    Generate confidential case number for HR complaints/cases.

    Args:
        case_type: Type of case (default: 'HR')
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'case_number', 'created_at', 'confidential', and 'details' keys

    POC Note: Uses random generation. Production would:
    - Use database sequence
    - Ensure uniqueness
    - Apply security classifications
    - Track in case management system
    """
    import random

    now = datetime.now()
    random.seed(now.timestamp())

    # Generate 6-digit case number
    number = f"{random.randint(100000, 999999)}"
    case_number = f"CASE-{number}"

    return {
        'case_number': case_number,
        'created_at': now.isoformat(),
        'confidential': True,
        'expires_at': None,
        'details': {
            'case_type': case_type,
            'status': 'open',
            'priority': 'normal'
        }
    }


def generate_employee_id(first_name: str = None, last_name: str = None,
                        **kwargs: Any) -> Dict[str, Any]:
    """
    Generate employee ID for new hire.

    Args:
        first_name: Employee first name (optional)
        last_name: Employee last name (optional)
        **kwargs: Additional parameters (e.g., department)

    Returns:
        Dict with 'employee_id', 'created_at', 'message', and 'details' keys

    POC Note: Uses random generation. Production would:
    - Query HRIS for next available ID
    - Follow company ID format rules
    - Check for duplicates
    - Create employee record
    """
    import random

    now = datetime.now()
    random.seed(f"{first_name}{last_name}{now.timestamp()}")

    # Generate 6-digit employee ID
    number = f"{random.randint(100000, 999999):06d}"
    employee_id = f"EMP-{number}"

    return {
        'employee_id': employee_id,
        'created_at': now.isoformat(),
        'message': f'Employee ID {employee_id} generated',
        'details': {
            'first_name': first_name,
            'last_name': last_name,
            'department': kwargs.get('department', 'unknown'),
            'status': 'active'
        }
    }


def create_onboarding_checklist(employee_id: str, role: str,
                               department: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Create onboarding checklist for new employee.

    Args:
        employee_id: Employee identifier
        role: Job role/title
        department: Department name (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'checklist_id', 'tasks', 'message', and 'details' keys

    POC Note: Returns generic checklist. Production would:
    - Customize by role and department
    - Integrate with onboarding platform
    - Assign tasks to HR/IT/Manager
    - Track completion status
    """
    import random

    random.seed(f"{employee_id}{role}")
    checklist_id = f"ONBOARD-{random.randint(10000, 99999)}"

    # Generic onboarding tasks
    tasks = [
        {
            'task_id': 1,
            'title': 'Complete new hire paperwork',
            'owner': 'hr',
            'due_days': 1,
            'status': 'pending',
            'priority': 'high'
        },
        {
            'task_id': 2,
            'title': 'Setup workstation and equipment',
            'owner': 'it',
            'due_days': 1,
            'status': 'pending',
            'priority': 'high'
        },
        {
            'task_id': 3,
            'title': 'Schedule orientation meeting',
            'owner': 'hr',
            'due_days': 1,
            'status': 'pending',
            'priority': 'medium'
        },
        {
            'task_id': 4,
            'title': 'Assign onboarding buddy',
            'owner': 'manager',
            'due_days': 3,
            'status': 'pending',
            'priority': 'medium'
        },
        {
            'task_id': 5,
            'title': 'Complete required training modules',
            'owner': 'employee',
            'due_days': 30,
            'status': 'pending',
            'priority': 'low'
        }
    ]

    return {
        'checklist_id': checklist_id,
        'tasks': tasks,
        'total_tasks': len(tasks),
        'completed_tasks': 0,
        'message': f'Onboarding checklist created with {len(tasks)} tasks',
        'details': {
            'employee_id': employee_id,
            'role': role,
            'department': department,
            'created_at': datetime.now().isoformat()
        }
    }


__all__ = [
    'calculate_total_days',
    'check_leave_balance',
    'check_team_conflicts',
    'verify_deadlines',
    'route_leave_approval',
    'update_team_calendar',
    'send_confirmation_email',
    'generate_case_number',
    'generate_employee_id',
    'create_onboarding_checklist',
]
