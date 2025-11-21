"""
Sandboxed execution environment for generated agents.

This module provides controlled execution of generated Python agents with:
- Restricted builtins to prevent unsafe operations
- Isolated namespace to prevent global state pollution
- Agent class discovery and instantiation
"""

import sys
from typing import Any, Dict, Optional, Type
from types import ModuleType


def create_safe_builtins() -> Dict[str, Any]:
    """
    Create a restricted builtins dictionary for safe execution.

    Removes dangerous functions that could:
    - Execute arbitrary code (eval, exec, compile)
    - Access file system (open, file)
    - Import arbitrary modules (__import__)
    - Modify system state

    Returns:
        Dictionary of allowed builtin functions
    """
    import builtins

    # Start with standard builtins
    safe_builtins = {
        # Basic types
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "frozenset": frozenset,
        "bytes": bytes,
        "bytearray": bytearray,

        # Essential functions
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "sorted": sorted,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "pow": pow,
        "divmod": divmod,

        # Type checking
        "isinstance": isinstance,
        "issubclass": issubclass,
        "type": type,
        "callable": callable,

        # String/conversion
        "chr": chr,
        "ord": ord,
        "hex": hex,
        "bin": bin,
        "oct": oct,
        "ascii": ascii,
        "repr": repr,
        "format": format,

        # Iteration
        "iter": iter,
        "next": next,
        "reversed": reversed,
        "slice": slice,

        # Object utilities
        "getattr": getattr,
        "setattr": setattr,
        "hasattr": hasattr,
        "delattr": delattr,
        "dir": dir,
        "vars": vars,
        "id": id,
        "hash": hash,

        # Printing (will be intercepted by LogInterceptor)
        "print": print,

        # Class/object construction (CRITICAL for defining classes!)
        "__build_class__": builtins.__build_class__,
        "__name__": "__main__",
        "object": object,
        "property": property,
        "staticmethod": staticmethod,
        "classmethod": classmethod,
        "super": super,

        # Common exceptions
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "AttributeError": AttributeError,
        "RuntimeError": RuntimeError,
        "IndexError": IndexError,
        "StopIteration": StopIteration,
        "NotImplementedError": NotImplementedError,
        "ZeroDivisionError": ZeroDivisionError,

        # Boolean
        "True": True,
        "False": False,
        "None": None,

        # Useful built-ins for agent logic
        "all": all,
        "any": any,
    }

    return safe_builtins


def create_safe_namespace() -> Dict[str, Any]:
    """
    Create an isolated namespace for agent execution.

    Returns:
        Dictionary with safe builtins and minimal globals
    """
    return {
        "__name__": "__main__",
        "__builtins__": create_safe_builtins(),
    }


def find_agent_class(namespace: Dict[str, Any]) -> Optional[Type]:
    """
    Find the agent class in the executed namespace.

    Looks for a class that has an 'execute' method, which is the
    standard interface for generated agents.

    Args:
        namespace: Namespace dictionary after executing agent code

    Returns:
        Agent class if found, None otherwise
    """
    for name, obj in namespace.items():
        # Skip private/magic names and builtins
        if name.startswith("_"):
            continue

        # Check if it's a class with execute method
        if isinstance(obj, type) and hasattr(obj, "execute"):
            return obj

    return None


def compile_agent_code(code: str, filename: str = "<agent>") -> Any:
    """
    Compile agent code with syntax checking.

    Args:
        code: Python code string to compile
        filename: Filename to use in error messages

    Returns:
        Compiled code object

    Raises:
        SyntaxError: If code has syntax errors
    """
    try:
        return compile(code, filename, "exec")
    except SyntaxError as e:
        raise SyntaxError(
            f"Generated agent code has syntax error at line {e.lineno}: {e.msg}"
        ) from e


def execute_in_sandbox(
    code: str,
    namespace: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed namespace.

    Args:
        code: Python code to execute
        namespace: Optional custom namespace (creates safe one if None)

    Returns:
        Namespace dictionary after execution

    Raises:
        SyntaxError: If code has syntax errors
        Exception: Any exception raised during execution
    """
    if namespace is None:
        namespace = create_safe_namespace()

    # Compile code first to catch syntax errors
    compiled = compile_agent_code(code)

    # Execute in sandbox
    exec(compiled, namespace)

    return namespace


def instantiate_agent(namespace: Dict[str, Any]) -> Any:
    """
    Find and instantiate the agent class from namespace.

    Args:
        namespace: Namespace after executing agent code

    Returns:
        Instantiated agent object

    Raises:
        ValueError: If no agent class found or instantiation fails
    """
    agent_class = find_agent_class(namespace)

    if agent_class is None:
        available_classes = [
            name for name, obj in namespace.items()
            if isinstance(obj, type) and not name.startswith("_")
        ]
        raise ValueError(
            f"No agent class with 'execute' method found in generated code. "
            f"Available classes: {available_classes}"
        )

    try:
        return agent_class()
    except Exception as e:
        raise ValueError(
            f"Failed to instantiate agent class '{agent_class.__name__}': {e}"
        ) from e
