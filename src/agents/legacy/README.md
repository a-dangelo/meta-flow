# Legacy Meta-Agent Implementations

This folder contains previous versions of the meta-agent implementation that were replaced during development.

## Files

### `meta_agent_toolcalling.py`
**Date**: 2025-11-09
**Status**: Deprecated

Original implementation that used OpenAI tool calling format to generate structured JSON output.

**Why it was replaced:**
- grok-4-fast-reasoning model struggled with tool calling complexity
- Generated workflows with empty `steps` arrays despite comprehensive prompts
- Tool schema was too complex for reliable structured output

**What we learned:**
- Tool calling is powerful but model-dependent
- Some models perform better with direct JSON generation
- Explicit, simple prompts often outperform complex schemas

**Prompt used:** `prompts/meta_agent_system.md` (190-line comprehensive prompt)

## Current Implementation

The current `meta_agent.py` uses direct JSON generation without tool calling:
- **Simpler approach**: Asks LLM directly for JSON string
- **Explicit prompt**: `prompts/simple_meta_agent_system_prompt.md` (103 lines)
- **Better results**: Works reliably on first attempt
- **Cleans markdown**: Removes code fences if LLM wraps JSON
- **Lower temperature**: 0.1 for consistency

## When to Use Tool Calling

Tool calling might still be useful for:
- Models with better tool support (GPT-4, Claude 3.5)
- When strict schema validation is needed at API level
- Complex nested structures that benefit from schema hints

## Migration Notes

If you need to switch back to tool calling:
1. Copy `meta_agent_toolcalling.py` to `meta_agent.py`
2. Update the prompt to use `meta_agent_system.md`
3. Test with a model that has better tool calling support
4. Consider using structured output mode if available
