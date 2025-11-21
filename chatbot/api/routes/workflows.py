"""
Workflow API routes for browsing available workflows.

Provides endpoints to list and retrieve workflow specifications.
"""

from fastapi import APIRouter, HTTPException, Query, status
import logging

from chatbot.api.models import WorkflowListResponse, WorkflowMetadataResponse
from chatbot.src.conversation.graph_hybrid import get_repository

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== API ENDPOINTS ====================

@router.get("/list", response_model=WorkflowListResponse)
async def list_workflows(
    access_level: str = Query(
        default="employee",
        description="User's access level (employee, manager, hr, admin)"
    ),
    category: str = Query(
        default=None,
        description="Filter by category (hr, it, finance, etc.)"
    )
):
    """
    List all accessible workflows for a user.

    Filters workflows based on:
    - User's access level (hierarchical: employee < manager < hr < admin)
    - Optional category filter

    Returns:
        List of workflow metadata with descriptions
    """
    try:
        repo = get_repository()

        # Get workflows filtered by access level
        workflows = repo.list_all_workflows(
            user_access_level=access_level,
            category=category
        )

        # Convert to response model
        workflow_responses = [
            WorkflowMetadataResponse(
                name=wf.name,
                description=wf.description,
                category=wf.category,
                access_level=wf.access_level,
                file_path=str(wf.file_path)
            )
            for wf in workflows
        ]

        logger.info(
            f"Listed {len(workflow_responses)} workflows "
            f"(access={access_level}, category={category})"
        )

        return WorkflowListResponse(
            workflows=workflow_responses,
            total=len(workflow_responses),
            access_level=access_level
        )

    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get("/{workflow_name}")
async def get_workflow(
    workflow_name: str,
    access_level: str = Query(
        default="employee",
        description="User's access level"
    )
):
    """
    Get detailed information about a specific workflow.

    Returns the full workflow specification and metadata.

    Args:
        workflow_name: Name of the workflow
        access_level: User's access level for permission check

    Returns:
        Workflow details including specification content

    Raises:
        404: If workflow not found or not accessible
    """
    try:
        repo = get_repository()

        # Get all accessible workflows
        accessible_workflows = repo.list_all_workflows(
            user_access_level=access_level
        )

        # Find requested workflow
        workflow = next(
            (wf for wf in accessible_workflows if wf.name == workflow_name),
            None
        )

        if not workflow:
            logger.warning(
                f"Workflow '{workflow_name}' not found or not accessible "
                f"(access_level={access_level})"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_name}' not found or not accessible"
            )

        # Get full specification
        spec_content = repo.get_workflow_spec(workflow_name)

        logger.info(
            f"Retrieved workflow '{workflow_name}' "
            f"(access_level={access_level})"
        )

        return {
            "name": workflow.name,
            "description": workflow.description,
            "category": workflow.category,
            "access_level": workflow.access_level,
            "file_path": str(workflow.file_path),
            "specification": spec_content,
            "confidence": workflow.confidence if hasattr(workflow, 'confidence') else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving workflow '{workflow_name}': {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workflow: {str(e)}"
        )


@router.get("/categories/list")
async def list_categories(
    access_level: str = Query(
        default="employee",
        description="User's access level"
    )
):
    """
    List all workflow categories available to a user.

    Returns unique categories from accessible workflows.

    Args:
        access_level: User's access level

    Returns:
        List of category names with workflow counts
    """
    try:
        repo = get_repository()

        # Get all accessible workflows
        workflows = repo.list_all_workflows(user_access_level=access_level)

        # Count workflows by category
        categories = {}
        for wf in workflows:
            if wf.category not in categories:
                categories[wf.category] = 0
            categories[wf.category] += 1

        # Convert to response format
        category_list = [
            {
                "name": category,
                "workflow_count": count,
                "description": f"{category.upper()} workflows"
            }
            for category, count in sorted(categories.items())
        ]

        logger.info(
            f"Listed {len(category_list)} categories "
            f"(access_level={access_level})"
        )

        return {
            "categories": category_list,
            "total": len(category_list),
            "access_level": access_level
        }

    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list categories: {str(e)}"
        )


@router.post("/reload")
async def reload_workflows():
    """
    Reload workflows from disk (for hot-reloading).

    Admin endpoint to refresh workflow repository without
    restarting the server.

    Note: In production, add authentication/authorization.

    Returns:
        Number of workflows loaded
    """
    try:
        repo = get_repository()
        repo.reload()

        workflow_count = len(repo.workflows)

        logger.info(f"Reloaded {workflow_count} workflows")

        return {
            "success": True,
            "message": f"Reloaded {workflow_count} workflows",
            "workflow_count": workflow_count
        }

    except Exception as e:
        logger.error(f"Error reloading workflows: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload workflows: {str(e)}"
        )
