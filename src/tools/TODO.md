# Automated Tool Implementation Generation for the Meta‑Agent

> Goal: extend the current meta‑agent so it can generate **real tool implementations** (not just stubs) from workflow specs + supplementary documentation, while preserving safety and keeping enterprise integrations under control.

This document assumes familiarity with the existing Meta‑Flow / meta‑agent codebase (`src/core`, `src/agents`, `src/generators`, `chatbot/src/integration`). It focuses on the Python side (agent generation) and treats the large‑scale document ingestion pipeline as context only.

---

## 1. Current Meta‑Agent Analysis

### 1.1 How the Meta‑Agent Processes Workflow Specs Today

**Inputs:**

- Structured `.txt` workflow specs (e.g. `specs/examples/simple_sequential.txt`, `chatbot/workflows/hr/file_expense_report.txt`) with sections:

  ```text
  Workflow: file_expense_report
  Description: Submit expense reports with automatic approval routing

  Inputs:
  - amount (float): Total expense amount in USD
  - date (string): Date of expense (YYYY-MM-DD format)
  - category (string): Expense type (meals, travel, supplies, other)
  - description (string): Brief description of the expense
  - employee_id (string): Employee identifier

  Steps:
  1. Validate expense amount is positive and less than $50000
  2. Check if category is in allowed list (meals, travel, supplies, other)
  3. Route for approval based on amount
  4. Generate unique reference number
  5. Log expense submission with timestamp
  6. Calculate estimated reimbursement date (7 business days from approval)

  Outputs:
  - reference_id (...)
  - status (...)
  - ...
  ```

**Pipeline:**

1. `MetaAgentClient.generate_agent_from_spec` (`chatbot/src/integration/meta_agent_client.py`):
   - Calls `run_meta_agent(raw_spec=spec_content, ...)` from `src.agents.graph`.
   - `run_meta_agent` uses an LLM (Claude) plus schema to parse the text spec into a **structured workflow spec dict**.

2. The dict is validated into a Pydantic **`WorkflowSpec`** model (`src/agents/models.WorkflowSpec`).

3. The `WorkflowSpec` is converted into JSON (for display) and passed to **`AgentGenerator`** (`src/generators/agent_generator.py`).
   - The `WorkflowSpec.workflow` field is an AST built from:
     - `ToolCall` nodes (atomic steps)
     - `SequentialWorkflow`, `ConditionalWorkflow`, `ParallelWorkflow`, `OrchestratorWorkflow` nodes (control‑flow containers).

4. `AgentGenerator.generate()` walks the AST and emits a Python agent class:
   - A class like `FileExpenseReportAgent` with:
     - `execute()` method that wires the control flow (validate → route → log → etc.).
     - One method per tool (`def validate_expense_amount(...)`, `def route_for_manager_approval(...)`, etc.).

5. For each tool, `AgentGenerator` currently generates a **stub**:

   ```python
   def validate_expense_amount(self, **kwargs) -> Any:
       """Tool: validate_expense_amount"""
       # TODO: Implement actual tool logic
       return {"status": "not_implemented", "data": kwargs}
   ```

### 1.2 Where Tool Calls Are Identified

- The meta‑agent parses the **Steps** section into `ToolCall` nodes.
  - Example: "Validate expense amount is positive and less than $50000" becomes a `ToolCall` with:
    - `tool_name = "validate_expense_amount"` (LLM‑inferred).
    - `parameters` often referencing inputs (`{{amount}}`).
- Control‑flow relationships (sequential order, conditionals) are encoded as:
  - `SequentialWorkflow.steps` lists.
  - `ConditionalWorkflow.condition` + `if_branch` / `else_branch`.

The AST **does know** that there is validation, routing, logging, etc. It treats each as a named tool call with parameter bindings.

### 1.3 Why Thresholds / Business Logic Are Dropped

The reason is subtle but important:

1. **Where thresholds live now**
   - In most specs, thresholds like "< 100" or "< 50000" are expressed in *free‑form natural language* in the `Steps` description.
   - The meta‑agent uses this language primarily to **name** the tool (`validate_expense_amount`) and decide where it sits in the flow.
   - The AST typically ends up with:

     ```json
     {
       "type": "tool_call",
       "tool_name": "validate_expense_amount",
       "parameters": {"amount": "{{amount}}"},
       "description": "Validate expense amount is positive and less than $50000"
     }
     ```

   - Note: the numeric threshold (50000) is **only in the description string**, not in a structured field.

2. **What `AgentGenerator` uses when generating tool methods**
   - It relies solely on:
     - `tool_name`
     - `parameters`
     - `assigns_to`
     - simple metadata like `description` (for comments).
   - There is **no structured representation** of thresholds / policies for it to use.

3. **Intentional design choice**
   - The generator was designed to be very conservative:
     - It does not parse free‑form descriptions into executable rules.
     - It does not attempt to infer external dependencies (DBs, APIs, auth).
   - Instead, it stops at a safe boundary: "Here’s the control flow and the tool API surface; you (the enterprise) implement the tool internals."

**Conclusion:** thresholds/business logic are not truly "ignored"; they never make it into a structured part of the AST in the first place. They remain in natural language descriptions, which the generator currently treats as comments only.

### 1.4 What the AST Captures vs. Discards

**Captured (structured):**

- Workflow:
  - Name, description, version.
  - Inputs/outputs (names, types, descriptions).
  - Root workflow node (Sequential / Conditional / Parallel / Orchestrator).
- For each `ToolCall`:
  - `tool_name`
  - `parameters` (mapping input names or context variables → arguments).
  - Optional `assigns_to` (where to store the result in the context).
  - Optional short `description`.
- Control‑flow:
  - Order of steps in `SequentialWorkflow.steps`.
  - Conditions in `ConditionalWorkflow.condition` (as strings, but syntactically constrained).
  - Branch topology (`if_branch`, `else_branch`, `branches` in `ParallelWorkflow`).

**Not structured / effectively discarded:**

- thresholds, validation ranges, and policies described inside **step descriptions**.
- detailed semantics of what a tool should do beyond its name and parameters.
- any explicit link to an external system (e.g., "this writes to `expenses` table" or "this calls SAP").

Because of this, the generator produces rich **orchestration** code but intentionally leaves **business logic** as human‑implemented TODOs.

---

## 2. Tool Generation Architecture

We want to extend the system so that it can generate realistic tool implementations automatically, while still being safe and auditable.

### 2.1 Information Extraction

We have several potential signal sources:

1. **Workflow specs themselves** (the `.txt` files)
   - Contain step‑level descriptions with thresholds, constraints, and routing rules.
   - Example: "If amount < 100, auto‑approve. If amount between 100 and 1000, manager review."

2. **Supplementary docs** (for a serious deployment):
   - Policy docs (PDF/Markdown) describing business rules.
   - DB schemas (SQL DDL, JSON schema) for the data model.
   - API specs (OpenAPI/Swagger) for external systems.
   - Existing internal code snippets or services.

3. **Code generator hints**
   - We can extend `ToolCall.metadata` or `WorkflowSpec.metadata` to carry explicit "implementation hints" (e.g., `policy_rules`, `db_table`, `api_endpoint`).

**Extracted artifacts we want:**

- Per tool:
  - **Contract:** name, input parameters, output shape.
  - **Policy rules:** thresholds, enums, allowed ranges.
  - **Side‑effect hints:** does it read/write DB, call API, send email, etc.

These can be represented as structured JSON attached to the AST, for example:

```json
{
  "tool_name": "route_for_approval",
  "parameters": [
    {"name": "amount", "type": "float"},
    {"name": "employee_level", "type": "string"}
  ],
  "policy": {
    "rules": [
      {"if": "amount < 100", "route": "auto_approve"},
      {"if": "100 <= amount <= 1000", "route": "manager"},
      {"if": "amount > 1000", "route": "director"}
    ]
  },
  "integration": {
    "type": "internal_service",
    "service_name": "approval_engine",
    "mode": "synchronous"
  }
}
```

This representation is crucial: once we have it, code generation is straightforward and safe.

### 2.2 Tool Implementation Strategies

#### Option 1 – Rule‑Based Generation

**Approach:**

- Implement deterministic parsers that:
  - Scan step descriptions and policy sections for patterns like:
    - `"positive and less than $50000"`
    - `"if amount < 100"`, `"if amount > 50000"`.
  - Map those to a small DSL or rule table.
- Generate tool code using templates:
  - Validation functions: `if amount <= 0: ...` etc.
  - Routing functions: chained `if/elif/else` based on numeric ranges or enums.

**Pros:**

- Fully deterministic, no LLM split‑brain risks.
- Easy to test; rules can be covered by unit tests.
- Great for common patterns: numeric thresholds, enum checks, simple routing.

**Cons:**

- Limited expressiveness; free‑form policies might not fit simple pattern rules.
- Hard to generalize to complex logic or external system integrations.
- Requires careful maintenance as pattern set grows.

**Feasibility:**

- High for a well‑defined subset (validation + threshold‑based routing).
- Good starting point to cover 60–80% of simple tools.

#### Option 2 – LLM‑Powered Tool Generation

**Approach:**

- Use an LLM (Claude/GPT) to synthesize tool implementations from:
  - Workflow spec text.
  - Supplementary docs (policy docs, schemas, API specs).
  - Example integrations or reference tools.
- Prompt the model with a strict format:

  > "Given this tool description and these contracts, generate a pure, side‑effect‑free Python function body that enforces the rules. Do not invent external systems; only use the given schema/API." 

**Pros:**

- Can handle more complex logic and nuanced policies.
- Easier to adapt to diverse domains (HR, finance, IT, etc.).

**Cons:**

- Risk of hallucinating unsupported integrations or misinterpreting policies.
- Harder to guarantee safety without strong constraints and verification.
- Requires a review process (human‑in‑the‑loop) or automated tests.

**Feasibility:**

- Good as a **copilot** for engineers, less ideal as fully autonomous generator without strong guardrails.

#### Option 3 – Hybrid Approach (Recommended)

**Approach:**

- Use **rule‑based generation** for common, well‑understood patterns:
  - Numeric thresholds, allowed categories, simple routes.
- Maintain a **curated tool library** for cross‑cutting concerns (audit logging, notifications, DB access) that is hand‑written.
- Use **LLM‑powered generation** for custom logic, but always:
  - Generate pure functions (no side effects) where possible.
  - Run them through tests derived from the spec (e.g., auto‑generated test cases from decision tables).
  - Require human review before promotion to "trusted" library tools.

**Pros:**

- Balances automation with safety.
- Reduces TODOs dramatically for common workflows.
- Provides a clear pathway to production‑ready tools.

**Cons:**

- More moving parts: rule extractor + LLM + review tools.
- Still requires engineering oversight.

#### Option 4 – Alternative: Library‑First with Semantic Matching

Another angle is to lean heavily on a growing **library of parameterized tools**:

- Tools like `validate_numeric_range`, `route_by_thresholds`, `validate_enum_members`, etc.
- Meta‑agent’s job becomes:
  - Map natural language steps to combinations of these generic tools + parameters.
- Tool implementations are hand‑crafted once; the meta‑agent mostly chooses and wires them.

This can be combined with Options 1 & 3 and is in fact compatible with the existing "tool library" plan.

### 2.3 Integration Points & External Systems

We need a way to distinguish:

- **Pure logic tools** (validation, routing, calculations) → safe to auto‑generate.
- **Integration tools** (DB, SAP, Workday, etc.) → should remain as stubs or thin adapters around real SDKs.

Proposed representation in the AST / metadata:

```json
{
  "tool_name": "log_expense_submission",
  "category": "integration",
  "integration": {
    "system": "internal_db",
    "resource": "expenses",
    "operation": "insert"
  }
}
```

Code generation behavior:

- For **pure logic** tools with sufficient contracts → generate full implementation.
- For **integration** tools → generate **interface stubs** that:
  - Have the correct signature.
  - Contain clear comments like `# TODO: integrate with SAP invoice API (see SAP_INTEGRATION.md)`.
  - Optionally call into a separate adapter layer if one exists.

### 2.4 Validation & Safety

Key mechanisms to keep auto‑generated tools safe and correct:

- **Type‑level safety:**
  - All generated tools have explicit type hints.
  - Pydantic models / TypedDicts for inputs/outputs.

- **Spec‑derived test cases:**
  - For each policy rule (e.g., `amount < 100`), generate unit tests that:
    - Pass in representative values and assert the correct branch/route.

- **Static analysis:**
  - Ensure generated code:
    - Does not import forbidden modules (`os`, `subprocess`, `requests` etc.) unless explicitly allowed.
    - Does not perform file or network IO unless designated as an integration stub.

- **Human review gates:**
  - Optionally require a review workflow for new or changed tools where an engineer:
    - Reviews the generated function and tests.
    - Approves promotion to the shared tool library.

---

## 3. Concrete Implementation Plan

We’ll implement automated tool generation in three phases.

### Phase 1 – Enhanced Spec Processing

**Goal:** capture thresholds and rules as structured metadata in the AST.

#### 3.1.1 Extend WorkflowSpec / ToolCall Models

- Add optional `metadata` to `ToolCall` in `src/agents/models.py` (if not already present) or use existing metadata structures.

  ```python
  class ToolCall(BaseModel):
      ...
      metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra tool metadata")
  ```

- Define a **ToolContract** structure (Pydantic model or TypedDict) representing extracted rules:

  ```python
  class ToolPolicyRule(BaseModel):
      condition: str  # e.g., "amount < 100"
      outcome: Dict[str, Any]

  class ToolContract(BaseModel):
      parameters: List[WorkflowInput]
      rules: List[ToolPolicyRule] = []
      category: Literal["logic", "integration", "io"] = "logic"
      integration: Optional[Dict[str, Any]] = None
  ```

#### 3.1.2 Rule Extraction from Specs

- Implement a **rule extraction component** (could be a function) that:
  - Runs after `run_meta_agent` but before `AgentGenerator`.
  - For each `ToolCall`:
    - Inspects its `description` and possibly the surrounding text in the spec.
    - Looks for specific patterns like:
      - `"less than $50000"` → `amount < 50000`.
      - `"auto-approve if amount < 100"` → `amount < 100 → route = auto_approve`.
    - Populates `ToolCall.metadata["contract"]` with a `ToolContract`.

- For a first version, this can be a **rule‑based parser** using regex and a small DSL:

  ```python
  def extract_contracts_from_spec(raw_spec: str, workflow_spec: WorkflowSpec) -> WorkflowSpec:
      # Walk steps / tool descriptions and attach contracts to each ToolCall
      ...
      return workflow_spec
  ```

- Longer‑term, you can plug in a library like **Trallie** here to extract richer decision logic.

#### 3.1.3 Example: Expense Amount Validation

Given the step description:

> "Validate expense amount is positive and less than $50000"

We want to produce:

```json
{
  "parameters": [
    {"name": "amount", "type": "float"}
  ],
  "rules": [
    {"condition": "amount <= 0", "outcome": {"valid": false, "reason": "Amount must be positive"}},
    {"condition": "amount > 50000", "outcome": {"valid": false, "reason": "Amount exceeds 50000"}}
  ],
  "category": "logic"
}
```

and attach it to the corresponding ToolCall.

### Phase 2 – Tool Generation Engine

**Goal:** generate actual Python bodies for tools based on contracts.

#### 3.2.1 Tool Generator Component

Add a new module:

- `src/generators/tool_generator.py`

Responsibilities:

- Accept a `ToolCall` + `ToolContract` + context (e.g., type info, available libraries).
- Produce a Python function body string implementing the rules.

Example signature:

```python
from src.agents.models import ToolCall
from typing import Optional


class ToolGenerator:
    def generate_tool_body(self, tool_call: ToolCall, contract: ToolContract) -> str:
        """Return Python code for the tool implementation body.

        Assumes a signature like: def <tool_name>(self, **kwargs) -> dict:
        """
        ...
```

For a rule‑based implementation, `generate_tool_body` can:

- Emit a header comment summarizing the rules.
- Emit `if/elif/else` statements mapping conditions to outcomes.
- End with a default success case if appropriate.

#### 3.2.2 Example Generated Tool Body

For `validate_expense_amount` with the contract above:

```python
def validate_expense_amount(self, *, amount: float, max_threshold: float = 50000.0) -> dict:
    """Validates expense amount against policy limits.

    Auto‑generated from workflow specification.
    """
    if amount <= 0:
        return {"valid": False, "reason": "Amount must be positive"}
    if amount > max_threshold:
        return {"valid": False, "reason": f"Amount exceeds limit of ${max_threshold}"}
    return {"valid": True, "reason": None}
```

#### 3.2.3 LLM‑Assisted Variant

If rule‑based extraction is insufficient, ToolGenerator could optionally:

- Call an LLM with:
  - Tool name + description.
  - Extracted policy text.
  - Optional schemas.
- Ask for a pure Python implementation constrained by guidelines.

In that case, `ToolGenerator` should still:

- Post‑process the code (static checks, pattern filters).
- Wrap it in tests.

### Phase 3 – Integration with AgentGenerator

**Goal:** wire tool generation into the existing agent codegen, so that stubs are replaced with real bodies when contracts exist.

#### 3.3.1 Modify AgentGenerator Tool Method Emission

Today, somewhere in `AgentGenerator`, per‑tool methods are emitted roughly as:

```python
def _generate_tool_method(self, node: ToolCall) -> str:
    lines = []
    lines.append(f"    def {node.tool_name}(self, **kwargs) -> Any:")
    lines.append(f"        \"\"\"Tool: {node.tool_name}\"\"\"")
    lines.append("        # TODO: Implement actual tool logic")
    lines.append("        return {\"status\": \"not_implemented\", \"data\": kwargs}")
    return "\n".join(lines)
```

Change this to:

```python
from src.generators.tool_generator import ToolGenerator

class AgentGenerator:
    def __init__(self, workflow_spec: WorkflowSpec):
        ...
        self.tool_generator = ToolGenerator()

    def _generate_tool_method(self, node: ToolCall) -> str:
        contract_data = node.metadata.get("contract") if hasattr(node, "metadata") else None
        if contract_data:
            contract = ToolContract.model_validate(contract_data)
            body = self.tool_generator.generate_tool_body(node, contract)
            return body

        # Fallback: improved stub with integration hint
        return self._generate_stub_tool_method(node)
```

Where `generate_tool_body` returns the full method definition, including docstring.

#### 3.3.2 File Structure for Generated Agents

No structural change is strictly required; generated agents can remain as single modules. For larger deployments, consider:

- `generated_agents/<workflow_name>/agent.py` – core agent class.
- `generated_agents/<workflow_name>/tools.py` – auto‑generated tool implementations.

In that model, `AgentGenerator` would:

- Emit the agent class in `agent.py`.
- Emit tool functions in `tools.py` and import them in `agent.py`.

This is optional but improves maintainability and diffability.

---

## 4. Supplementary Documentation Format

To make tool generation robust, firms should provide structured docs alongside specs.

### 4.1 Database Integration

**Recommended formats:**

- **SQL DDL** for relevant tables, e.g.:

  ```sql
  CREATE TABLE expenses (
      id SERIAL PRIMARY KEY,
      reference_id TEXT UNIQUE NOT NULL,
      employee_id TEXT NOT NULL,
      amount NUMERIC(12, 2) NOT NULL,
      category TEXT NOT NULL,
      description TEXT,
      status TEXT NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT now()
  );
  ```

- Or **JSON Schema** describing tables/collections.

Tool generator usage:

- For tools like `log_expense_submission`, generate code that:
  - Builds parameter dicts matching the schema.
  - Calls an abstract `db.insert("expenses", record)` instead of direct SQL.

### 4.2 API Integration

**Recommended formats:**

- **OpenAPI/Swagger** specs for external services.
- Authentication docs (OAuth2, API keys, etc.).

Tool generator usage:

- Generate interface stubs like:

  ```python
  def notify_manager_via_api(manager_id: str, payload: dict) -> dict:
      """Stub for HR notification API (see HR_API.md for details)."""
      # TODO: integrate with /notifications/manager endpoint
      return {"status": "queued"}
  ```

- Only if specifically allowed, and with human review, generate real HTTP client code.

### 4.3 Business Logic & Policies

**Recommended formats:**

- Markdown or text with **decision tables**:

  ```markdown
  | Amount Range        | Route      |
  |---------------------|-----------|
  | < 100               | auto      |
  | 100 to 1000         | manager   |
  | > 1000              | director  |
  ```

- Plain text annotated with simple markers:

  ```text
  POLICY: expense_approval
  RULE: amount < 100 -> route=auto
  RULE: 100 <= amount <= 1000 -> route=manager
  RULE: amount > 1000 -> route=director
  ```

Tool generator usage:

- Convert these tables/rules directly into `ToolContract.policy.rules`.

### 4.4 System Connections

Provide a **catalog** of systems with metadata:

```json
{
  "systems": [
    {"name": "SAP", "type": "erp", "integration": "api", "docs": "sap_integration.md"},
    {"name": "Workday", "type": "hr", "integration": "api"},
    {"name": "internal_db", "type": "postgres", "integration": "db"}
  ]
}
```

Tool generator usage:

- Tag tools that mention these systems as "integration" category.
- Generate stubs with explicit references to integration docs.

---

## 5. Realistic Example Walkthrough – Expense Report Workflow

### 5.1 Inputs

#### 5.1.1 Workflow Spec

We already have `file_expense_report` spec (simplified here):

```text
Workflow: file_expense_report
Description: Submit expense reports with automatic approval routing

Inputs:
- amount (float): Total expense amount in USD
- date (string): Date of expense (YYYY-MM-DD format)
- category (string): Expense type (meals, travel, supplies, other)
- description (string): Brief description of the expense
- employee_id (string): Employee identifier

Steps:
1. Validate expense amount is positive and less than $50000
2. Check if category is in allowed list (meals, travel, supplies, other)
3. Route for approval based on amount:
   - If amount < 100, auto-approve
   - If amount between 100 and 1000, flag for manager review
   - If amount > 1000, flag for director review
4. Generate unique reference number
5. Log expense submission with timestamp
6. Calculate estimated reimbursement date (7 business days from approval)

Outputs:
- reference_id (string): Unique expense reference
- status (string): Approval status
- estimated_reimbursement (string): Expected reimbursement date
- message (string): Confirmation message for employee
```

#### 5.1.2 Supplementary Docs (Mocked)

- Policy doc:

  ```text
  POLICY: expense_amount_limits
  RULE: amount must be > 0
  RULE: amount must be < 50000
  ```

- Approval routing table:

  ```markdown
  | Amount Range | Route      |
  |--------------|-----------|
  | < 100        | auto      |
  | 100-1000     | manager   |
  | > 1000       | director  |
  ```

- DB schema snippet:

  ```sql
  TABLE: expenses
  COLUMNS: reference_id, employee_id, amount, category, description, status, created_at
  ```

### 5.2 Processing Steps

1. **Meta‑agent AST creation** – same as today:
   - `WorkflowSpec` with `ToolCall`s:
     - `validate_expense_amount`
     - `check_category_allowed`
     - `route_for_approval`
     - `generate_reference_number`
     - `log_expense_submission`
     - `calculate_reimbursement_date`

2. **Rule extraction**:
   - For `validate_expense_amount`:
     - From step text + POLICY doc extract rules:
       - `amount <= 0 → invalid ("Amount must be positive")`
       - `amount >= 50000 → invalid ("Amount must be < 50000")`
   - For `route_for_approval`:
     - From routing table extract rules:
       - `< 100 → route=auto_approve`
       - `100-1000 → route=manager`
       - `> 1000 → route=director`
   - For `log_expense_submission`:
     - From schema snippet mark tool as `integration` with `system=internal_db`, `table=expenses`.

3. **Attach contracts**:
   - Each relevant `ToolCall.metadata["contract"]` is populated.

4. **Tool generation**:
   - `ToolGenerator` creates full implementations for logic tools, interface stubs for integration tools.

5. **Agent generation**:
   - `AgentGenerator` emits final code.

### 5.3 Example Output – Generated Tool Implementation

```python
class FileExpenseReportAgent:
    ...

    def validate_expense_amount(self, *, amount: float, max_threshold: float = 50000.0) -> dict:
        """Validates expense amount against policy limits.

        Auto‑generated from expense_approval policy.
        """
        if amount <= 0:
            return {"valid": False, "reason": "Amount must be positive"}
        if amount >= max_threshold:
            return {
                "valid": False,
                "reason": f"Amount exceeds limit of ${max_threshold}",
            }
        return {"valid": True, "reason": None}

    def route_for_approval(self, *, amount: float) -> dict:
        """Route an expense for approval based on amount.

        Auto‑generated from approval routing table.
        """
        if amount < 100:
            return {"route": "auto_approve", "reason": "Amount < 100"}
        if 100 <= amount <= 1000:
            return {"route": "manager", "reason": "100 <= amount <= 1000"}
        return {"route": "director", "reason": "Amount > 1000"}

    def log_expense_submission(self, **kwargs) -> dict:
        """Log expense submission to the expenses table.

        Integration stub – connect to your database here.
        """
        # TODO: integrate with expenses table (see DB_INTEGRATION.md)
        record = {**kwargs, "status": "recorded"}
        return record
```

Now the agent can execute end‑to‑end with realistic validation and routing, while still leaving DB integration as an explicit, well‑documented boundary.

---

## 6. Trade‑offs & Recommendations

### 6.1 What Should Be Auto‑Generated

**High‑confidence categories (good automation candidates):**

- **Validation tools:**
  - Numeric range checks (amount, duration).
  - Enum membership (categories, statuses).
  - Date ordering and ranges.
- **Routing tools:**
  - Threshold‑based decision making (auto vs manager vs director).
  - Simple conditional branches based on flags or levels.
- **Calculations:**
  - Business‑day arithmetic.
  - Simple scoring / aggregations defined clearly in specs.

These can be safely auto‑generated from rules with strong tests.

### 6.2 What Should Remain Stubs

**Categories that should stay human‑implemented (at least initially):**

- **System integrations:**
  - DB writes/reads, queues, message buses.
  - ERP/HR/CRM APIs (SAP, Workday, Salesforce, internal microservices).
- **Security‑sensitive logic:**
  - Permission checks.
  - Authentication flows.
- **Highly domain‑specific rules** that aren’t easily captured in simple patterns.

For these, the generator should produce:

- Clear interface stubs with docstrings.
- References to integration docs.
- Optional hooks into a hand‑crafted adapter layer.

### 6.3 Recommended Approach

- Start with the **hybrid approach**:
  - Add rule extraction + contract metadata (Phase 1).
  - Implement a rule‑based `ToolGenerator` for validation, routing, and simple calculations (Phase 2).
  - Keep integration tools as stubs with improved comments.
  - Optionally add an LLM‑assisted mode for generating more complex logic, but always behind tests and human review.

- This yields quick wins:
  - For workflows like expense reports and leave requests, 70–80% of tools become real implementations automatically.
  - The remaining TODOs are clearly marked as enterprise‑specific – exactly where stakeholders need to plug in their systems.

### 6.4 Success Metrics

- % of tools in a given workflow that are fully implemented vs. stubbed.
- % of test cases (derived from policies) that pass for auto‑generated tools.
- Reduction in manual engineering time per workflow (compared to hand‑coding tools).
- Number of production incidents traced to auto‑generated logic (should be near zero with tests + review).

---

## 7. Missing Pieces & Next Steps

### 7.1 Components to Build

1. **Rule Extraction Layer (Phase 1):**
   - Functions to parse workflow specs + policy docs into `ToolContract` structures.
   - Integration into `MetaAgentClient` or a new orchestration layer so contracts are attached before codegen.

2. **ToolContract Models:**
   - Pydantic models / TypedDicts to represent policies, thresholds, and integration hints.
   - Extension of `ToolCall.metadata` to carry these contracts.

3. **ToolGenerator (Phase 2):**
   - Rule‑based generation of tool bodies.
   - Optional LLM‑assisted generation behind a flag.
   - Unit tests for generated bodies (especially for numeric thresholds and routing logic).

4. **AgentGenerator Integration (Phase 3):**
   - Replace stub generation with contract‑aware tool methods.
   - Optional support for splitting agents into `agent.py` + `tools.py`.

5. **Supplementary Docs Conventions:**
   - Templates and example docs for policies, schemas, and integration catalogs.
   - Developer documentation (`TOOLS_INTEGRATION.md`) explaining how to add docs and how they drive tool generation.

### 7.2 Infrastructure & Tooling

- Test harness for generated agents:
  - Given a spec, run the full pipeline and execute the agent with sample inputs.
  - Assert invariants derived from the spec (e.g., amounts above threshold route to director).
- Code quality checks for generated code:
  - Run `mypy`/`ruff`/`flake8` (if configured) on generated modules.

### 7.3 Rough Complexity Estimate

Very approximate, assuming 1–2 senior engineers familiar with the codebase:

- **Phase 1 (spec processing + contracts):** 2–3 weeks
  - Building rule extractors for numeric thresholds and simple routing.
  - Wiring metadata through the AST and into the generator.
- **Phase 2 (ToolGenerator + tests):** 3–4 weeks
  - Implementing generation for validation, routing, and business‑day calculations.
  - Writing unit/integration tests.
- **Phase 3 (integration + docs + polish):** 2–3 weeks
  - Hooking into AgentGenerator, refining stubs, writing documentation.

Total: **7–10 person‑weeks** for a robust MVP of automated tool generation, excluding any sophisticated LLM‑assisted logic or large‑scale integration with 20K+ real docs.

### 7.4 Prioritized Action Items

1. **Add metadata/contract support to `ToolCall` and `WorkflowSpec`.**
2. **Implement a first rule extractor for numeric thresholds and simple routing.**
3. **Build a basic `ToolGenerator` that turns contracts into Python function bodies (validation + routing).**
4. **Integrate `ToolGenerator` into `AgentGenerator` to replace stub methods when contracts exist.**
5. **Create tests and a demo for the expense report workflow showing end‑to‑end tool generation.**

Once these steps are in place, we can iteratively:

- Expand rule coverage.
- Add optional LLM‑assisted generation for complex tools.
- Tighten safety and testing for production scenarios.