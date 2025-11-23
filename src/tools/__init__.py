"""
Tool Library for Meta-Flow Generated Agents

This module provides mock implementations of common business tools used across
generated agents. Tools are organized by domain (expense, hr, it, common) and
registered in TOOL_REGISTRY for agent generator integration.

Design Principles:
- Mock data only (no external APIs)
- Deterministic outputs (fixed seeds for random values)
- Structured return values (TypedDict)
- Clear POC limitations in docstrings
- Never raise exceptions (return error objects instead)

Usage in Generated Agents:
    from src.tools.expense import validate_expense_amount

    result = validate_expense_amount(amount=1500.00)
    if result['valid']:
        # proceed with expense
"""

# Tool Registry: Maps tool names to their module paths
# Used by agent_generator.py to determine which tools have library implementations
TOOL_REGISTRY = {
    # Finance/Expense Tools (8 tools)
    'validate_expense_amount': 'src.tools.expense',
    'check_category_allowed': 'src.tools.expense',
    'route_for_approval': 'src.tools.expense',
    'generate_reference_number': 'src.tools.expense',
    'log_expense_submission': 'src.tools.expense',
    'calculate_reimbursement_date': 'src.tools.expense',
    'calculate_quarterly_impact': 'src.tools.expense',
    'set_review_date': 'src.tools.expense',

    # HR Tools (10 tools)
    'calculate_total_days': 'src.tools.hr',
    'check_leave_balance': 'src.tools.hr',
    'check_team_conflicts': 'src.tools.hr',
    'verify_deadlines': 'src.tools.hr',
    'route_leave_approval': 'src.tools.hr',
    'update_team_calendar': 'src.tools.hr',
    'send_confirmation_email': 'src.tools.hr',
    'generate_case_number': 'src.tools.hr',
    'generate_employee_id': 'src.tools.hr',
    'create_onboarding_checklist': 'src.tools.hr',

    # IT Tools (10 tools)
    'validate_description': 'src.tools.it',
    'check_asset_exists': 'src.tools.it',
    'search_knowledge_base': 'src.tools.it',
    'create_ticket': 'src.tools.it',
    'route_to_team': 'src.tools.it',
    'assign_to_agent': 'src.tools.it',
    'validate_hardware_type': 'src.tools.it',
    'calculate_hardware_cost': 'src.tools.it',
    'calculate_software_cost': 'src.tools.it',
    'set_delivery_date': 'src.tools.it',

    # Common/Utility Tools (5 tools)
    'send_notification': 'src.tools.common',
    'generate_ticket_id': 'src.tools.common',
    'log_submission': 'src.tools.common',
    'format_message': 'src.tools.common',
    'validate_input': 'src.tools.common',
}

__all__ = ['TOOL_REGISTRY']
