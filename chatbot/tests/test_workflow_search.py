"""Debug test for workflow search."""

import sys
from pathlib import Path

# Add chatbot to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chatbot.src.workflow_matching.repository import WorkflowRepository


def test_workflow_loading():
    """Test that workflows are loaded correctly."""
    print("=" * 80)
    print("TEST: Workflow Loading")
    print("=" * 80)

    workflows_dir = Path(__file__).parent.parent / "workflows"
    print(f"\nWorkflows directory: {workflows_dir}")
    print(f"Exists: {workflows_dir.exists()}")

    if workflows_dir.exists():
        txt_files = list(workflows_dir.rglob("*.txt"))
        print(f"\nFound {len(txt_files)} .txt files:")
        for f in txt_files:
            print(f"  - {f.relative_to(workflows_dir)}")

    print("\nInitializing repository...")
    repo = WorkflowRepository(workflows_dir)

    print(f"\nLoaded workflows: {len(repo.workflows)}")
    for wf in repo.workflows:
        print(f"  - {wf.name}")
        print(f"      Description: {wf.description}")
        print(f"      Access: {wf.access_level}")
        print(f"      Category: {wf.category}")

    print(f"\nEmbeddings shape: {repo.embeddings.shape if repo.embeddings is not None else 'None'}")

    print("\n" + "=" * 80)
    print("TEST: Semantic Search")
    print("=" * 80)

    test_queries = [
        "I need to submit an expense report",
        "submit expense",
        "expense approval",
        "I want to request time off",
        "IT support ticket"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        workflow, confidence = repo.find_by_intent(query, "employee")

        if workflow:
            print(f"  ✓ Matched: {workflow.name} ({confidence:.2%})")
        else:
            print(f"  ✗ No match (confidence: {confidence:.2%})")

    print("\n" + "=" * 80)
    print("✓ Workflow search test completed")
    print("=" * 80)


if __name__ == "__main__":
    test_workflow_loading()
