"""
IT Support Tools for Meta-Flow Agents

Mock implementations of IT ticketing, hardware, and software management tools.
All functions use deterministic mock data for POC demo purposes.

POC Limitations:
- No actual ITSM or asset management system integration
- Fixed hardware/software catalog and pricing
- Mock knowledge base search results
- Simple routing rules (no skill-based assignment)
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta


def validate_description(description: str, min_length: int = 10, **kwargs: Any) -> Dict[str, Any]:
    """
    Validate IT issue description meets minimum requirements.

    Args:
        description: Issue description text
        min_length: Minimum required length (default: 10 characters)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'valid', 'message', and 'details' keys

    POC Note: Basic validation only. Production would:
    - Check for required fields
    - Scan for sensitive information
    - Validate against known issue patterns
    - Suggest similar existing tickets
    """
    if not description or not isinstance(description, str):
        return {
            'valid': False,
            'message': 'Description is required and must be text',
            'details': {'description': description}
        }

    description = description.strip()
    length = len(description)

    if length < min_length:
        return {
            'valid': False,
            'message': f'Description must be at least {min_length} characters (current: {length})',
            'details': {
                'description': description,
                'length': length,
                'min_length': min_length
            }
        }

    return {
        'valid': True,
        'message': 'Description meets requirements',
        'details': {
            'length': length,
            'min_length': min_length,
            'word_count': len(description.split())
        }
    }


def check_asset_exists(asset_id: str, asset_type: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Check if asset/device exists in asset management system.

    Args:
        asset_id: Asset identifier or serial number
        asset_type: Type of asset (optional: 'laptop', 'desktop', 'monitor', etc.)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'exists', 'asset_info', 'message', and 'details' keys

    POC Note: Returns mock asset data. Production would:
    - Query actual asset management database
    - Verify current assignment
    - Check warranty status
    - Provide maintenance history
    """
    import random

    # POC: Randomly determine if asset exists (deterministic based on ID)
    random.seed(asset_id)
    exists = random.random() < 0.8  # 80% chance asset exists

    if exists:
        # Generate mock asset info
        asset_types = ['laptop', 'desktop', 'monitor', 'phone', 'tablet']
        mock_type = asset_type if asset_type else random.choice(asset_types)

        return {
            'exists': True,
            'asset_info': {
                'asset_id': asset_id,
                'asset_type': mock_type,
                'model': f'{mock_type.title()} Pro Model',
                'assigned_to': f'EMP-{random.randint(100000, 999999)}',
                'purchase_date': '2023-01-15',
                'warranty_expiry': '2026-01-15',
                'status': 'active'
            },
            'message': f'Asset {asset_id} found in system',
            'details': {'query': asset_id, 'type': mock_type}
        }
    else:
        return {
            'exists': False,
            'asset_info': None,
            'message': f'Asset {asset_id} not found in system',
            'details': {
                'query': asset_id,
                'suggestion': 'Please verify the asset ID or serial number'
            }
        }


def search_knowledge_base(query: str, category: str = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Search IT knowledge base for similar issues and solutions.

    Args:
        query: Search query string
        category: Optional category filter ('hardware', 'software', 'network')
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'results', 'result_count', 'message', and 'details' keys

    POC Note: Returns mock KB articles. Production would:
    - Perform semantic search on actual KB
    - Rank by relevance and success rate
    - Include resolution steps
    - Track article usage and feedback
    """
    import random

    # POC: Generate mock KB articles
    random.seed(query)
    result_count = random.randint(0, 3)

    if result_count == 0:
        return {
            'results': [],
            'result_count': 0,
            'message': 'No similar issues found in knowledge base',
            'details': {
                'query': query,
                'category': category,
                'suggestion': 'This may be a new issue requiring investigation'
            }
        }

    # Generate mock articles
    article_types = [
        'login issues', 'password reset', 'software installation',
        'network connectivity', 'printer setup', 'email configuration'
    ]

    results = [
        {
            'article_id': f'KB-{random.randint(10000, 99999)}',
            'title': f'How to resolve {random.choice(article_types)}',
            'relevance_score': round(random.uniform(0.6, 0.95), 2),
            'category': category or random.choice(['hardware', 'software', 'network']),
            'resolution_rate': round(random.uniform(0.7, 0.95), 2),
            'last_updated': '2024-11-01'
        }
        for _ in range(result_count)
    ]

    # Sort by relevance
    results.sort(key=lambda x: x['relevance_score'], reverse=True)

    return {
        'results': results,
        'result_count': result_count,
        'message': f'Found {result_count} similar issue(s) in knowledge base',
        'details': {
            'query': query,
            'category': category,
            'top_relevance': results[0]['relevance_score'] if results else 0
        }
    }


def create_ticket(title: str, description: str, priority: str = 'normal',
                 category: str = 'general', **kwargs: Any) -> Dict[str, Any]:
    """
    Create IT support ticket.

    Args:
        title: Ticket title/summary
        description: Detailed description
        priority: Priority level ('low', 'normal', 'high', 'urgent')
        category: Category ('hardware', 'software', 'network', 'general')
        **kwargs: Additional parameters (e.g., requester_id, asset_id)

    Returns:
        Dict with 'ticket_id', 'created_at', 'message', and 'details' keys

    POC Note: Returns mock ticket. Production would:
    - Create actual ticket in ITSM system
    - Send notifications to IT team
    - Apply SLA timers
    - Link to asset records
    """
    import random

    now = datetime.now()
    date_part = now.strftime('%Y%m%d')

    random.seed(f"{title}{now.timestamp()}")
    suffix = f"{random.randint(0, 9999):04d}"

    ticket_id = f"TKT-{date_part}-{suffix}"

    # Map priority to SLA hours
    sla_hours = {
        'urgent': 2,
        'high': 8,
        'normal': 24,
        'low': 72
    }

    due_date = now + timedelta(hours=sla_hours.get(priority.lower(), 24))

    return {
        'ticket_id': ticket_id,
        'created_at': now.isoformat(),
        'due_date': due_date.isoformat(),
        'message': f'Ticket {ticket_id} created successfully',
        'details': {
            'title': title,
            'description': description,
            'priority': priority,
            'category': category,
            'status': 'open',
            'sla_hours': sla_hours.get(priority.lower(), 24),
            'requester_id': kwargs.get('requester_id', 'unknown'),
            'asset_id': kwargs.get('asset_id')
        }
    }


def route_to_team(category: str, priority: str = 'normal', **kwargs: Any) -> Dict[str, Any]:
    """
    Route IT ticket to appropriate support team.

    Args:
        category: Ticket category
        priority: Priority level
        **kwargs: Additional parameters (e.g., subcategory, keywords)

    Returns:
        Dict with 'team', 'queue', 'message', and 'details' keys

    POC Note: Uses simple routing rules. Production would:
    - Use AI/ML for intelligent routing
    - Check team availability and workload
    - Consider skill matching
    - Support escalation rules
    """
    # POC: Route based on category
    routing_map = {
        'hardware': {'team': 'desktop_support', 'queue': 'hardware_queue'},
        'software': {'team': 'application_support', 'queue': 'software_queue'},
        'network': {'team': 'network_operations', 'queue': 'network_queue'},
        'security': {'team': 'security_team', 'queue': 'security_queue'},
        'general': {'team': 'help_desk', 'queue': 'general_queue'}
    }

    category_lower = category.lower()
    routing = routing_map.get(category_lower, routing_map['general'])

    # Escalate urgent tickets
    if priority.lower() == 'urgent':
        routing['escalated'] = True
        routing['sla_monitoring'] = True

    return {
        'team': routing['team'],
        'queue': routing['queue'],
        'escalated': routing.get('escalated', False),
        'message': f"Routed to {routing['team']}",
        'details': {
            'category': category,
            'priority': priority,
            'routing_rule': 'category_based'
        }
    }


def assign_to_agent(team: str, priority: str = 'normal',
                   skills_required: List[str] = None, **kwargs: Any) -> Dict[str, Any]:
    """
    Assign ticket to available IT support agent.

    Args:
        team: Team name
        priority: Priority level
        skills_required: List of required skills (optional)
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'assigned_to', 'agent_info', 'message', and 'details' keys

    POC Note: Returns mock agent assignment. Production would:
    - Check real-time agent availability
    - Consider workload balancing
    - Match skills to requirements
    - Support round-robin or priority-based assignment
    """
    import random

    # POC: Generate mock agent assignment
    random.seed(f"{team}{priority}")

    agent_names = ['Alice Chen', 'Bob Smith', 'Carol Johnson', 'David Lee', 'Emma Wilson']
    agent_name = random.choice(agent_names)
    agent_id = f"AGENT-{random.randint(1000, 9999)}"

    return {
        'assigned_to': agent_id,
        'agent_info': {
            'agent_id': agent_id,
            'name': agent_name,
            'team': team,
            'current_workload': random.randint(3, 8),
            'skills': skills_required or ['general_support'],
            'availability': 'available'
        },
        'message': f'Assigned to {agent_name} ({agent_id})',
        'details': {
            'team': team,
            'priority': priority,
            'assignment_method': 'workload_based'
        }
    }


def validate_hardware_type(hardware_type: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Validate that requested hardware type is supported.

    Args:
        hardware_type: Type of hardware being requested
        **kwargs: Additional parameters (ignored)

    Returns:
        Dict with 'valid', 'supported', 'message', and 'details' keys

    POC Note: Uses fixed hardware catalog. Production would:
    - Query approved vendor catalog
    - Check budget codes
    - Verify compatibility
    - Include procurement lead times
    """
    # POC: Approved hardware types
    SUPPORTED_HARDWARE = {
        'laptop': {'name': 'Standard Laptop', 'models': ['Dell Latitude', 'HP EliteBook']},
        'desktop': {'name': 'Desktop Computer', 'models': ['Dell OptiPlex', 'HP ProDesk']},
        'monitor': {'name': 'Monitor', 'models': ['Dell UltraSharp', 'LG UltraWide']},
        'keyboard': {'name': 'Keyboard', 'models': ['Logitech MX Keys', 'Microsoft Ergonomic']},
        'mouse': {'name': 'Mouse', 'models': ['Logitech MX Master', 'Microsoft Precision']},
        'headset': {'name': 'Headset', 'models': ['Jabra Evolve', 'Plantronics Voyager']},
        'webcam': {'name': 'Webcam', 'models': ['Logitech C920', 'Microsoft LifeCam']},
        'dock': {'name': 'Docking Station', 'models': ['Dell WD19', 'HP Thunderbolt Dock']}
    }

    hardware_lower = hardware_type.lower().strip()

    if hardware_lower in SUPPORTED_HARDWARE:
        hw_info = SUPPORTED_HARDWARE[hardware_lower]
        return {
            'valid': True,
            'supported': True,
            'message': f"{hw_info['name']} is supported",
            'details': {
                'hardware_type': hardware_type,
                'available_models': hw_info['models'],
                'category': hw_info['name']
            }
        }
    else:
        return {
            'valid': False,
            'supported': False,
            'message': f"'{hardware_type}' is not in the approved hardware catalog",
            'details': {
                'hardware_type': hardware_type,
                'supported_types': list(SUPPORTED_HARDWARE.keys())
            }
        }


def calculate_hardware_cost(hardware_type: str, quantity: int = 1, **kwargs: Any) -> Dict[str, Any]:
    """
    Calculate cost for hardware request.

    Args:
        hardware_type: Type of hardware
        quantity: Number of units (default: 1)
        **kwargs: Additional parameters (e.g., model, specifications)

    Returns:
        Dict with 'unit_cost', 'total_cost', 'message', and 'details' keys

    POC Note: Uses fixed pricing. Production would:
    - Query actual vendor pricing
    - Apply volume discounts
    - Include tax and shipping
    - Check budget availability
    """
    # POC: Mock hardware pricing (USD)
    HARDWARE_PRICES = {
        'laptop': 1200.00,
        'desktop': 800.00,
        'monitor': 300.00,
        'keyboard': 100.00,
        'mouse': 50.00,
        'headset': 150.00,
        'webcam': 80.00,
        'dock': 200.00
    }

    hardware_lower = hardware_type.lower().strip()
    unit_cost = HARDWARE_PRICES.get(hardware_lower, 0.00)

    if unit_cost == 0:
        return {
            'unit_cost': 0.00,
            'total_cost': 0.00,
            'message': f"No pricing found for '{hardware_type}'",
            'details': {
                'hardware_type': hardware_type,
                'quantity': quantity,
                'error': 'unknown_hardware_type'
            }
        }

    total_cost = unit_cost * quantity

    return {
        'unit_cost': unit_cost,
        'total_cost': total_cost,
        'currency': 'USD',
        'message': f'Total cost: ${total_cost:,.2f} for {quantity} unit(s)',
        'details': {
            'hardware_type': hardware_type,
            'quantity': quantity,
            'includes_tax': False,
            'includes_shipping': False
        }
    }


def calculate_software_cost(software_name: str, license_type: str = 'user',
                           quantity: int = 1, **kwargs: Any) -> Dict[str, Any]:
    """
    Calculate cost for software license request.

    Args:
        software_name: Software product name
        license_type: License type ('user', 'device', 'concurrent')
        quantity: Number of licenses (default: 1)
        **kwargs: Additional parameters (e.g., subscription_term)

    Returns:
        Dict with 'unit_cost', 'total_cost', 'message', and 'details' keys

    POC Note: Uses mock pricing. Production would:
    - Query actual vendor contracts
    - Check existing license pool
    - Apply enterprise discounts
    - Consider subscription vs perpetual
    """
    # POC: Mock software pricing per user/month (USD)
    SOFTWARE_PRICES = {
        'microsoft_office': 12.50,
        'adobe_creative_cloud': 54.99,
        'slack': 8.00,
        'zoom': 14.99,
        'jira': 10.00,
        'confluence': 5.00,
        'salesforce': 25.00,
        'tableau': 70.00
    }

    software_lower = software_name.lower().strip().replace(' ', '_')
    unit_cost = SOFTWARE_PRICES.get(software_lower, 10.00)  # Default $10/mo

    subscription_term = kwargs.get('subscription_term', 12)  # months
    monthly_cost = unit_cost * quantity
    total_cost = monthly_cost * subscription_term

    return {
        'unit_cost': unit_cost,
        'monthly_cost': monthly_cost,
        'total_cost': total_cost,
        'currency': 'USD',
        'message': f'Total cost: ${total_cost:,.2f} for {quantity} license(s) x {subscription_term} months',
        'details': {
            'software_name': software_name,
            'license_type': license_type,
            'quantity': quantity,
            'subscription_term': subscription_term,
            'billing': 'monthly'
        }
    }


def set_delivery_date(hardware_type: str, priority: str = 'normal',
                     **kwargs: Any) -> Dict[str, Any]:
    """
    Calculate delivery date for hardware request.

    Args:
        hardware_type: Type of hardware
        priority: Priority level ('low', 'normal', 'high', 'urgent')
        **kwargs: Additional parameters (e.g., location)

    Returns:
        Dict with 'delivery_date', 'business_days', 'message', and 'details' keys

    POC Note: Uses simple calculation. Production would:
    - Check vendor stock levels
    - Consider shipping logistics
    - Account for procurement approval time
    - Support expedited shipping
    """
    # POC: Lead times by priority (business days)
    lead_times = {
        'urgent': 1,
        'high': 3,
        'normal': 7,
        'low': 10
    }

    business_days = lead_times.get(priority.lower(), 7)

    # Calculate delivery date (skip weekends)
    current_date = datetime.now()
    days_added = 0
    while days_added < business_days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            days_added += 1

    return {
        'delivery_date': current_date.strftime('%Y-%m-%d'),
        'business_days': business_days,
        'message': f'Expected delivery: {current_date.strftime("%Y-%m-%d")}',
        'details': {
            'hardware_type': hardware_type,
            'priority': priority,
            'order_date': datetime.now().strftime('%Y-%m-%d'),
            'expedited': priority.lower() in ['urgent', 'high']
        }
    }


__all__ = [
    'validate_description',
    'check_asset_exists',
    'search_knowledge_base',
    'create_ticket',
    'route_to_team',
    'assign_to_agent',
    'validate_hardware_type',
    'calculate_hardware_cost',
    'calculate_software_cost',
    'set_delivery_date',
]
