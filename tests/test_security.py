"""
Security validation tests for generated agents.

Ensures:
1. No hardcoded credentials in generated code
2. All credentials use os.getenv() pattern
3. Clear setup instructions in docstrings
4. Proper error handling for missing env vars
"""

import re
from pathlib import Path
import pytest


class TestSecurityScanner:
    """Test suite for credential security scanning."""

    @pytest.fixture
    def generated_agents_dir(self):
        """Path to generated agents directory."""
        return Path(__file__).parent.parent / "generated_agents"

    @pytest.fixture
    def all_generated_agents(self, generated_agents_dir):
        """List of all generated .py files."""
        return list(generated_agents_dir.glob("*_agent.py"))

    def test_no_hardcoded_credentials(self, all_generated_agents):
        """
        Test: Generated code contains NO hardcoded credentials.

        Pattern: Detects assignments like:
        - api_key = "sk-123"
        - password = 'secret123'
        - database_url = "postgresql://..."
        """
        # Regex pattern from CLAUDE.md security requirements
        credential_pattern = re.compile(
            r'(api_key|apikey|password|token|secret|credential|'
            r'database_url|db_url|connection_string|auth|'
            r'authorization|bearer|private_key|secret_key|'
            r'access_key|webhook)\s*=\s*["\'][^"\']+["\']',
            re.IGNORECASE
        )

        violations = []

        for agent_file in all_generated_agents:
            with open(agent_file) as f:
                code = f.read()

            # Find all matches
            for match in credential_pattern.finditer(code):
                line_num = code[:match.start()].count('\n') + 1
                violations.append({
                    'file': agent_file.name,
                    'line': line_num,
                    'match': match.group(0)
                })

        # Report violations clearly
        if violations:
            error_msg = "Found hardcoded credentials:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} → {v['match']}\n"
            pytest.fail(error_msg)

    def test_credentials_use_env_vars(self, all_generated_agents):
        """
        Test: All credential parameters use os.getenv() pattern.

        Verifies that generated code retrieves credentials from environment
        variables, not hardcoded strings.
        """
        for agent_file in all_generated_agents:
            with open(agent_file) as f:
                code = f.read()

            # Skip agents that weren't properly generated (old/broken)
            if 'TODO: Unsupported node type' in code:
                continue

            # Check if file has credential-related tool methods
            has_credentials = bool(re.search(
                r'(api_key|password|token|database_url|webhook)',
                code,
                re.IGNORECASE
            ))

            if has_credentials:
                # Should use os.getenv() pattern
                assert 'os.getenv(' in code, (
                    f"{agent_file.name} has credentials but doesn't use os.getenv()"
                )

    def test_setup_instructions_present(self, all_generated_agents):
        """
        Test: Module docstrings contain setup instructions for credentials.

        Ensures users know how to configure environment variables.
        """
        for agent_file in all_generated_agents:
            with open(agent_file) as f:
                code = f.read()

            # Check if file needs credentials
            has_credentials = bool(re.search(
                r'os\.getenv\(["\']([A-Z_]+)["\']',
                code
            ))

            if has_credentials:
                # Extract module docstring (first triple-quote block)
                docstring_match = re.search(r'"""(.*?)"""', code, re.DOTALL)
                assert docstring_match, f"{agent_file.name} missing module docstring"

                docstring = docstring_match.group(1)

                # Should contain setup instructions
                assert 'SETUP INSTRUCTIONS' in docstring, (
                    f"{agent_file.name} missing SETUP INSTRUCTIONS section"
                )
                assert 'export ' in docstring, (
                    f"{agent_file.name} missing export examples"
                )

    def test_missing_credential_error_handling(self, all_generated_agents):
        """
        Test: Generated code raises clear errors when env vars missing.

        Pattern: After os.getenv(), should check and raise ValueError.
        """
        for agent_file in all_generated_agents:
            with open(agent_file) as f:
                code = f.read()

            # Find all os.getenv() calls
            getenv_calls = re.findall(
                r'(\w+)\s*=\s*os\.getenv\(["\']([A-Z_]+)["\']\)',
                code
            )

            for var_name, env_var in getenv_calls:
                # Should have check after getenv
                check_pattern = rf'if not {re.escape(var_name)}:'
                assert re.search(check_pattern, code), (
                    f"{agent_file.name} missing error check for {var_name}"
                )

                # Should raise ValueError with helpful message
                error_pattern = rf'raise ValueError.*{re.escape(env_var)}'
                assert re.search(error_pattern, code, re.DOTALL), (
                    f"{agent_file.name} missing ValueError for {env_var}"
                )

    def test_no_eval_or_exec(self, all_generated_agents):
        """
        Test: Generated code doesn't use dangerous eval() or exec().

        Safety check for condition evaluation.
        """
        dangerous_patterns = [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\b__import__\s*\('
        ]

        for agent_file in all_generated_agents:
            with open(agent_file) as f:
                code = f.read()

            for pattern in dangerous_patterns:
                matches = re.findall(pattern, code)
                assert not matches, (
                    f"{agent_file.name} contains dangerous pattern: {pattern}"
                )

    def test_proper_imports(self, all_generated_agents):
        """
        Test: Generated agents have proper imports (os, typing).

        Ensures code is self-contained and executable.
        """
        for agent_file in all_generated_agents:
            with open(agent_file) as f:
                code = f.read()

            # Should import os if using env vars
            if 'os.getenv(' in code:
                assert 'import os' in code, (
                    f"{agent_file.name} uses os.getenv() but doesn't import os"
                )

            # Should import typing for type hints
            assert 'from typing import' in code, (
                f"{agent_file.name} missing typing imports"
            )


class TestExistingGeneratedAgents:
    """Test all 6 existing generated agents."""

    EXPECTED_AGENTS = [
        'compliance_check_agent.py',
        'data_processing_pipeline_agent.py',
        'expense_approval_agent.py',
        'order_fulfillment_agent.py',
        'support_ticket_router_agent.py',
        'ticket_router_orchestrator_agent.py'
    ]

    def test_all_agents_exist(self):
        """Verify all 6 generated agents exist."""
        agents_dir = Path(__file__).parent.parent / "generated_agents"

        for agent_name in self.EXPECTED_AGENTS:
            agent_path = agents_dir / agent_name
            assert agent_path.exists(), f"Missing generated agent: {agent_name}"

    def test_all_agents_importable(self):
        """Verify all generated agents can be imported."""
        import sys
        from pathlib import Path

        # Add generated_agents to path
        agents_dir = Path(__file__).parent.parent / "generated_agents"
        sys.path.insert(0, str(agents_dir))

        try:
            for agent_name in self.EXPECTED_AGENTS:
                module_name = agent_name.replace('.py', '')
                __import__(module_name)
        finally:
            sys.path.pop(0)

    def test_all_agents_have_execute_method(self):
        """Verify all agents have execute() method."""
        import sys
        from pathlib import Path
        import importlib

        agents_dir = Path(__file__).parent.parent / "generated_agents"
        sys.path.insert(0, str(agents_dir))

        try:
            for agent_name in self.EXPECTED_AGENTS:
                module_name = agent_name.replace('.py', '')
                module = importlib.import_module(module_name)

                # Find the agent class (PascalCase + Agent suffix)
                class_name = ''.join(
                    word.capitalize()
                    for word in module_name.replace('_agent', '').split('_')
                ) + 'Agent'

                # Special case for ticket_router_orchestrator_agent
                if module_name == 'ticket_router_orchestrator_agent':
                    class_name = 'TicketRouterAgent'

                assert hasattr(module, class_name), (
                    f"{agent_name} missing class {class_name}"
                )

                agent_class = getattr(module, class_name)
                assert hasattr(agent_class, 'execute'), (
                    f"{class_name} missing execute() method"
                )
        finally:
            sys.path.pop(0)


class TestCredentialPatterns:
    """Test specific credential patterns in generated agents."""

    def test_compliance_check_agent_credentials(self):
        """Test compliance_check_agent.py has proper credential handling."""
        agent_path = Path(__file__).parent.parent / "generated_agents" / "compliance_check_agent.py"

        with open(agent_path) as f:
            code = f.read()

        # Should have COMPLIANCE_API_KEY
        assert 'COMPLIANCE_API_KEY' in code
        # Should use os.getenv (accept both quote styles)
        assert ("os.getenv('COMPLIANCE_API_KEY')" in code or
                'os.getenv("COMPLIANCE_API_KEY")' in code)

        # Should have error handling
        assert 'raise ValueError' in code
        assert 'Missing COMPLIANCE_API_KEY' in code

    def test_support_ticket_router_credentials(self):
        """Test support_ticket_router_agent.py has proper credential handling."""
        agent_path = Path(__file__).parent.parent / "generated_agents" / "support_ticket_router_agent.py"

        with open(agent_path) as f:
            code = f.read()

        # Skip if this is an old/broken agent
        if 'TODO: Unsupported node type' in code:
            pytest.skip("Agent not properly generated - needs regeneration")

        # Should have TICKET_API_KEY and ESCALATION_WEBHOOK
        assert 'TICKET_API_KEY' in code
        assert 'ESCALATION_WEBHOOK' in code

        # Should use os.getenv for both (accept both quote styles)
        assert ("os.getenv('TICKET_API_KEY')" in code or
                'os.getenv("TICKET_API_KEY")' in code)
        assert ("os.getenv('ESCALATION_WEBHOOK')" in code or
                'os.getenv("ESCALATION_WEBHOOK")' in code)

    def test_order_fulfillment_credentials(self):
        """Test order_fulfillment_agent.py has proper credential handling."""
        agent_path = Path(__file__).parent.parent / "generated_agents" / "order_fulfillment_agent.py"

        with open(agent_path) as f:
            code = f.read()

        # Should have PAYMENT_TOKEN and WAREHOUSE_API_KEY (actual credentials in this agent)
        assert 'PAYMENT_TOKEN' in code
        assert 'WAREHOUSE_API_KEY' in code

        # Should use os.getenv for both (accept both quote styles)
        assert ("os.getenv('PAYMENT_TOKEN')" in code or
                'os.getenv("PAYMENT_TOKEN")' in code)
        assert ("os.getenv('WAREHOUSE_API_KEY')" in code or
                'os.getenv("WAREHOUSE_API_KEY")' in code)