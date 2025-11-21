"""Tools for LLM agent to use during conversation."""

from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

from chatbot.src.workflow_matching.repository import WorkflowRepository
from chatbot.src.integration.meta_agent_client import MetaAgentClient


# Initialize repository singleton
_repository = None


def get_repository() -> WorkflowRepository:
    """Get or create workflow repository singleton."""
    global _repository
    if _repository is None:
        workflows_dir = Path(__file__).parent.parent.parent / "workflows"
        _repository = WorkflowRepository(workflows_dir)
    return _repository


@tool
def search_workflows(query: str, user_access_level: str = "employee") -> str:
    """
    Search for workflows matching the user's intent.

    Use this when the user describes what they want to do (e.g., "submit expense",
    "request time off", "report IT issue").

    Args:
        query: Natural language description of what the user wants to do
        user_access_level: User's access level (employee, manager, hr, admin)

    Returns:
        Information about matched workflow or list of available workflows if no match
    """
    repo = get_repository()

    workflow, confidence = repo.find_by_intent(query, user_access_level)

    if workflow:
        return (
            f"Found workflow: {workflow.name}\n"
            f"Description: {workflow.description}\n"
            f"Confidence: {confidence:.1%}\n"
            f"Category: {workflow.category}\n"
            f"File: {workflow.file_path}"
        )
    else:
        # No match - list available workflows
        all_workflows = repo.list_all_workflows(user_access_level)
        workflow_list = "\n".join(
            f"  • {wf.name}: {wf.description}"
            for wf in all_workflows[:5]
        )
        return (
            f"No workflow matched with sufficient confidence ({confidence:.1%}).\n"
            f"Available workflows:\n{workflow_list}"
        )


@tool
async def generate_agent_from_workflow(workflow_name: str) -> str:
    """
    Generate a Python agent from a workflow specification.

    Use this after finding a workflow to generate the executable agent code.
    This will create the agent and extract required parameters.

    Args:
        workflow_name: Name of the workflow (from search_workflows)

    Returns:
        JSON string with agent details including required parameters
    """
    import json

    repo = get_repository()

    # Get workflow spec content
    spec_content = repo.get_workflow_spec(workflow_name)
    if not spec_content:
        return f"Error: Workflow '{workflow_name}' not found"

    # Generate agent using meta-agent pipeline
    client = MetaAgentClient()

    try:
        json_output, python_code = await client.generate_agent_from_spec(
            spec_content,
            provider="claude"
        )

        # Extract parameter information
        inputs = json_output.get("inputs", [])
        parameters = [
            {
                "name": inp["name"],
                "type": inp.get("type", "string"),
                "description": inp.get("description", ""),
                "required": True
            }
            for inp in inputs
        ]

        return json.dumps({
            "workflow_name": workflow_name,
            "status": "generated",
            "parameters": parameters,
            "agent_code_length": len(python_code),
            "message": f"Agent generated successfully. Requires {len(parameters)} parameters."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "workflow_name": workflow_name,
            "status": "error",
            "error": str(e)
        })


@tool
def get_parameter_info(workflow_name: str) -> str:
    """
    Get detailed parameter information for a workflow.

    Use this to understand what information you need to collect from the user.

    Args:
        workflow_name: Name of the workflow

    Returns:
        Formatted parameter list with descriptions
    """
    # This is a placeholder - in real implementation, this would
    # read from generated agent or workflow spec
    return (
        "Parameter collection info will be available after "
        "calling generate_agent_from_workflow()"
    )


@tool
async def execute_workflow_agent(
    workflow_name: str,
    parameters: dict
) -> str:
    """
    Execute a generated workflow agent with collected parameters.

    Use this ONLY after:
    1. Generating the agent with generate_agent_from_workflow()
    2. Collecting all required parameters from the user

    Args:
        workflow_name: Name of the workflow
        parameters: Dictionary of parameter name -> value

    Returns:
        Execution results or error message
    """
    import json

    # For MVP, return simulation
    return json.dumps({
        "workflow": workflow_name,
        "status": "simulated",
        "message": "Execution simulated for MVP. Real execution to be implemented in Day 2.",
        "parameters_received": parameters,
        "reference_id": f"REF-{hash(str(parameters)) % 10000:04d}"
    }, indent=2)


# List of all tools for agent binding
CHATBOT_TOOLS = [
    search_workflows,
    generate_agent_from_workflow,
    get_parameter_info,
    execute_workflow_agent
]
