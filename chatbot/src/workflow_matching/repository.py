"""Workflow repository with semantic search for intent matching."""

import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class WorkflowMetadata:
    """Immutable workflow metadata."""

    name: str
    description: str
    file_path: Path
    access_level: str
    category: str
    confidence: float = 0.0


class WorkflowRepository:
    """
    Repository for workflow specifications with semantic search.

    Features:
    - Loads workflows from chatbot/workflows/ directory
    - Pre-computes embeddings for fast semantic search
    - Filters by access level (employee, manager, hr, admin)
    - Returns best match with confidence score
    """

    def __init__(
        self,
        workflows_dir: Path,
        model_name: str = "BAAI/bge-small-en-v1.5",
        confidence_threshold: float = 0.60
    ):
        """
        Initialize workflow repository.

        Args:
            workflows_dir: Path to workflows directory
            model_name: Sentence transformer model name (default: BAAI/bge-small-en-v1.5)
            confidence_threshold: Minimum confidence for match (0.0-1.0, default: 0.60)

        Note:
            Using BGE-small-en-v1.5 model (~130MB) for space efficiency.
            Provides good semantic search performance for English workflows.
            For multilingual support, use BAAI/bge-m3 (2.3GB).
        """
        self.workflows_dir = Path(workflows_dir)
        self.confidence_threshold = confidence_threshold

        # Load sentence transformer model with BGE-M3 optimization
        self.encoder = SentenceTransformer(model_name)
        if "bge" in model_name.lower():
            self.encoder.max_seq_length = 512  # BGE-M3 optimal sequence length

        # Load workflows and build embeddings cache
        self.workflows = self._load_workflows()
        self.embeddings = self._build_embeddings()

    def _load_workflows(self) -> list[WorkflowMetadata]:
        """Load all workflow specifications from directory."""
        workflows = []

        for txt_file in self.workflows_dir.rglob("*.txt"):
            metadata = self._parse_workflow_metadata(txt_file)
            if metadata:
                workflows.append(metadata)

        return workflows

    def _parse_workflow_metadata(self, file_path: Path) -> Optional[WorkflowMetadata]:
        """
        Parse workflow metadata from specification file.

        Extracts:
        - Workflow name
        - Description
        - Access level (from optional Access: field)
        - Category (from optional Category: field or directory name)
        """
        try:
            content = file_path.read_text()

            # Extract required fields
            name_match = re.search(r"^Workflow:\s*(.+)$", content, re.MULTILINE)
            desc_match = re.search(r"^Description:\s*(.+)$", content, re.MULTILINE)

            if not name_match or not desc_match:
                return None

            # Extract optional metadata fields
            access_match = re.search(r"^Access:\s*(.+)$", content, re.MULTILINE)
            category_match = re.search(r"^Category:\s*(.+)$", content, re.MULTILINE)

            # Default access level and category
            access_level = access_match.group(1).strip() if access_match else "employee"
            category = category_match.group(1).strip() if category_match else file_path.parent.name

            return WorkflowMetadata(
                name=name_match.group(1).strip(),
                description=desc_match.group(1).strip(),
                file_path=file_path,
                access_level=access_level,
                category=category
            )
        except Exception:
            return None

    def _build_embeddings(self) -> np.ndarray:
        """
        Pre-compute embeddings for all workflow descriptions.

        Uses BGE-M3 model which produces 1024-dimensional embeddings
        optimized for semantic search across multiple languages.
        """
        descriptions = [wf.description for wf in self.workflows]
        return self.encoder.encode(descriptions, convert_to_numpy=True, normalize_embeddings=True)

    def find_by_intent(
        self,
        user_input: str,
        user_access_level: str = "employee"
    ) -> tuple[Optional[WorkflowMetadata], float]:
        """
        Find best matching workflow using semantic search.

        Args:
            user_input: Natural language intent from user
            user_access_level: User's access level for filtering

        Returns:
            Tuple of (matched workflow or None, confidence score)
        """
        if not self.workflows:
            return None, 0.0

        # Filter workflows by access level
        accessible_workflows = self._filter_by_access(user_access_level)

        if not accessible_workflows:
            return None, 0.0

        # Encode user query with normalization for consistent similarity scores
        query_embedding = self.encoder.encode([user_input], convert_to_numpy=True, normalize_embeddings=True)

        # Get embeddings for accessible workflows
        accessible_indices = [
            i for i, wf in enumerate(self.workflows)
            if wf in accessible_workflows
        ]
        accessible_embeddings = self.embeddings[accessible_indices]

        # Compute cosine similarity
        similarities = cosine_similarity(query_embedding, accessible_embeddings)[0]

        # Find best match
        best_idx = np.argmax(similarities)
        confidence = float(similarities[best_idx])

        if confidence >= self.confidence_threshold:
            matched_workflow = accessible_workflows[best_idx]
            # Return workflow with confidence score
            return (
                WorkflowMetadata(
                    name=matched_workflow.name,
                    description=matched_workflow.description,
                    file_path=matched_workflow.file_path,
                    access_level=matched_workflow.access_level,
                    category=matched_workflow.category,
                    confidence=confidence
                ),
                confidence
            )

        return None, confidence

    def _filter_by_access(self, user_access_level: str) -> list[WorkflowMetadata]:
        """
        Filter workflows by user access level.

        Access hierarchy:
        - employee: Can access workflows marked "employee"
        - manager: Can access "employee" + "manager"
        - hr: Can access "employee" + "manager" + "hr"
        - admin: Can access all workflows
        """
        access_hierarchy = {
            "employee": ["employee"],
            "manager": ["employee", "manager"],
            "hr": ["employee", "manager", "hr"],
            "admin": ["employee", "manager", "hr", "admin"]
        }

        allowed_levels = access_hierarchy.get(user_access_level, ["employee"])

        return [
            wf for wf in self.workflows
            if wf.access_level in allowed_levels
        ]

    def list_all_workflows(
        self,
        user_access_level: str = "employee",
        category: Optional[str] = None
    ) -> list[WorkflowMetadata]:
        """
        List all accessible workflows, optionally filtered by category.

        Args:
            user_access_level: User's access level
            category: Optional category filter (hr, it, finance, etc.)

        Returns:
            List of accessible workflow metadata
        """
        workflows = self._filter_by_access(user_access_level)

        if category:
            workflows = [wf for wf in workflows if wf.category == category]

        return sorted(workflows, key=lambda w: w.name)

    def get_workflow_spec(self, workflow_name: str) -> Optional[str]:
        """
        Get full workflow specification content by name.

        Args:
            workflow_name: Name of workflow

        Returns:
            Full specification text or None if not found
        """
        workflow = next(
            (wf for wf in self.workflows if wf.name == workflow_name),
            None
        )

        if workflow:
            return workflow.file_path.read_text()

        return None

    def reload(self) -> None:
        """Reload workflows and rebuild embeddings (for hot-reloading)."""
        self.workflows = self._load_workflows()
        self.embeddings = self._build_embeddings()
