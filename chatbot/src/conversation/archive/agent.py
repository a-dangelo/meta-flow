"""LLM-powered conversational agent with tool calling."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from chatbot.src.conversation.tools import CHATBOT_TOOLS


SYSTEM_PROMPT = """You are a helpful enterprise workflow automation assistant. Your role is to help employees complete internal processes by:

1. **Understanding Intent**: Listen to what the user wants to do
2. **Finding Workflows**: Use search_workflows() to find the appropriate workflow
3. **Generating Agents**: Use generate_agent_from_workflow() to create the automation
4. **Collecting Parameters**: Ask the user for required information in a natural, conversational way
5. **Executing Workflows**: Use execute_workflow_agent() to run the workflow with collected parameters

**Conversation Guidelines**:
- Be friendly and professional
- Ask clarifying questions when needed
- Collect parameters one at a time or in groups (your choice)
- Confirm important actions before executing
- Provide clear status updates

**Important**:
- ALWAYS use search_workflows() first to find the right workflow
- ALWAYS call generate_agent_from_workflow() after finding a workflow
- ONLY call execute_workflow_agent() after collecting ALL required parameters
- Keep track of what parameters you've collected and what's still needed

**Example Flow**:
User: "I need to submit an expense"
You: [search_workflows("expense")] → Found expense_approval workflow
You: [generate_agent_from_workflow("expense_approval")] → Needs: amount, date, category, department, receipt_url, employee_id
You: "I can help with that! Please provide:
     • Expense amount (in USD)
     • Date of expense
     • Category (travel, meals, office, equipment, other)
     • Your department
     • Receipt URL
     • Your employee ID"
User: "$450, today, meals, Engineering, https://..., EMP123"
You: [execute_workflow_agent("expense_approval", {...})] → Success!
You: "Your expense report #EXP-2847 has been submitted. Manager approval is pending."
"""


def create_chatbot_agent(
    model_name: str = "claude-sonnet-4-20250514",
    temperature: float = 0.7
):
    """
    Create LLM-powered conversational agent with tool calling.

    Args:
        model_name: Anthropic model to use
        temperature: Sampling temperature (0-1)

    Returns:
        Compiled ReAct agent with tools and memory
    """
    # Initialize Claude
    llm = ChatAnthropic(
        model=model_name,
        temperature=temperature
    )

    # Create ReAct agent with tools
    agent = create_react_agent(
        llm,
        tools=CHATBOT_TOOLS,
        state_modifier=SYSTEM_PROMPT
    )

    return agent


async def run_agent_turn(
    agent,
    user_message: str,
    conversation_history: list
) -> tuple[str, list]:
    """
    Run one turn of the conversational agent.

    Args:
        agent: Compiled ReAct agent
        user_message: User's message
        conversation_history: Previous messages in conversation

    Returns:
        Tuple of (agent_response, updated_conversation_history)
    """
    # Build message list
    messages = conversation_history + [HumanMessage(content=user_message)]

    # Run agent
    response = await agent.ainvoke({"messages": messages})

    # Extract agent's response
    agent_messages = response["messages"]
    last_message = agent_messages[-1]

    # Update conversation history
    updated_history = agent_messages

    return last_message.content, updated_history
