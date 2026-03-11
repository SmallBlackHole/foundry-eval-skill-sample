"""
Math Solver Agent - An agent that solves common math problems.
Uses Microsoft Agent Framework with Azure AI Foundry.
Ready for deployment to Foundry Hosted Agent service.
"""

import asyncio
import logging
import math
import os
import statistics
from typing import Annotated

from dotenv import load_dotenv
from agent_framework.azure import AzureAIAgentClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Math tools
# ---------------------------------------------------------------------------

def solve_quadratic(
    a: Annotated[float, "Coefficient a (must be non-zero)"],
    b: Annotated[float, "Coefficient b"],
    c: Annotated[float, "Coefficient c"],
) -> str:
    """Solve a quadratic equation ax^2 + bx + c = 0 and return the roots."""
    if a == 0:
        return "Error: Coefficient 'a' must be non-zero for a quadratic equation."
    discriminant = b ** 2 - 4 * a * c
    if discriminant > 0:
        x1 = (-b + math.sqrt(discriminant)) / (2 * a)
        x2 = (-b - math.sqrt(discriminant)) / (2 * a)
        return f"Two real roots: x1 = {x1}, x2 = {x2}"
    elif discriminant == 0:
        x = -b / (2 * a)
        return f"One repeated root: x = {x}"
    else:
        real = -b / (2 * a)
        imag = math.sqrt(abs(discriminant)) / (2 * a)
        return f"Two complex roots: x1 = {real} + {imag}i, x2 = {real} - {imag}i"


def basic_arithmetic(
    expression: Annotated[str, "A basic arithmetic expression to evaluate, e.g. '2 + 3 * 4'"],
) -> str:
    """
    Safely evaluate a basic arithmetic expression containing numbers and
    operators +, -, *, /, **, (, ).
    """
    allowed_chars = set("0123456789+-*/.() eE")
    if not all(ch in allowed_chars for ch in expression):
        return "Error: Expression contains unsupported characters. Only numbers and +, -, *, /, **, () are allowed."
    try:
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
        return f"Result: {result}"
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


def compute_statistics(
    numbers: Annotated[list[float], "A list of numbers to compute statistics for"],
) -> str:
    """Compute mean, median, mode, standard deviation, min, and max for a list of numbers."""
    if not numbers:
        return "Error: The list of numbers is empty."
    try:
        mean = statistics.mean(numbers)
        median = statistics.median(numbers)
        try:
            mode = statistics.mode(numbers)
        except statistics.StatisticsError:
            mode = "no unique mode"
        stdev = statistics.pstdev(numbers)
        return (
            f"Count: {len(numbers)}\n"
            f"Mean: {mean}\n"
            f"Median: {median}\n"
            f"Mode: {mode}\n"
            f"Std Dev (population): {stdev}\n"
            f"Min: {min(numbers)}\n"
            f"Max: {max(numbers)}"
        )
    except Exception as exc:
        return f"Error computing statistics: {exc}"


def compute_factorial(
    n: Annotated[int, "A non-negative integer"],
) -> str:
    """Compute the factorial of a non-negative integer n."""
    if n < 0:
        return "Error: Factorial is not defined for negative numbers."
    if n > 1000:
        return "Error: Input too large. Please use n <= 1000."
    return f"{n}! = {math.factorial(n)}"


def compute_gcd_lcm(
    a: Annotated[int, "First integer"],
    b: Annotated[int, "Second integer"],
) -> str:
    """Compute the GCD and LCM of two integers."""
    if a == 0 and b == 0:
        return "GCD(0, 0) is undefined. LCM(0, 0) = 0."
    gcd = math.gcd(a, b)
    lcm = abs(a * b) // gcd if gcd != 0 else 0
    return f"GCD({a}, {b}) = {gcd}\nLCM({a}, {b}) = {lcm}"


def convert_base(
    number: Annotated[str, "The number to convert (prefix with 0x for hex, 0b for binary, 0o for octal, or plain decimal)"],
    to_base: Annotated[int, "Target base: 2, 8, 10, or 16"],
) -> str:
    """Convert a number between bases (binary, octal, decimal, hexadecimal)."""
    try:
        value = int(number, 0)
    except ValueError:
        return f"Error: Could not parse '{number}' as a number."
    if to_base == 2:
        return f"Result: {bin(value)}"
    elif to_base == 8:
        return f"Result: {oct(value)}"
    elif to_base == 10:
        return f"Result: {value}"
    elif to_base == 16:
        return f"Result: {hex(value)}"
    else:
        return "Error: Supported bases are 2, 8, 10, and 16."


# ---------------------------------------------------------------------------
# Math tools list (for reuse)
# ---------------------------------------------------------------------------

MATH_TOOLS = [
    solve_quadratic,
    basic_arithmetic,
    compute_statistics,
    compute_factorial,
    compute_gcd_lcm,
    convert_base,
]

AGENT_INSTRUCTIONS = """You are a helpful math solver agent. You can solve a wide range of common math problems.

Your capabilities include:
1. **Basic Arithmetic** — Evaluate arithmetic expressions (addition, subtraction, multiplication, division, exponents).
2. **Quadratic Equations** — Solve equations of the form ax^2 + bx + c = 0, including complex roots.
3. **Statistics** — Compute mean, median, mode, standard deviation, min, and max for a set of numbers.
4. **Factorials** — Compute n! for non-negative integers.
5. **GCD & LCM** — Find the greatest common divisor and least common multiple of two integers.
6. **Base Conversion** — Convert numbers between binary, octal, decimal, and hexadecimal.

When a user presents a math problem:
- Identify which tool is most appropriate and always use it for every math query to compute the solution, never relying solely on manual calculations when a tool is available.
- Explicitly state which tool was used after its invocation and provide its direct output before rephrasing the answer.
- For arithmetic expressions, pass the full expression string as written to the basic_arithmetic tool.
- Show the work and explain the result clearly.
- Verify the final answer matches the tool output before responding to the user.
- If the problem is ambiguous, ask for clarification.
- For problems outside your tool capabilities, reason step by step using your own knowledge.

Be concise, accurate, and educational in your responses."""


# ---------------------------------------------------------------------------
# Agent factory (importable from other modules)
# ---------------------------------------------------------------------------

def create_agent(
    *,
    project_endpoint: str | None = None,
    model_deployment_name: str | None = None,
):
    """Create and return the math-solver agent along with its async resources.

    When called without arguments the function reads configuration from
    environment variables (``PROJECT_ENDPOINT`` and ``MODEL_DEPLOYMENT_NAME``).
    ``load_dotenv`` is called automatically so a ``.env`` file is picked up.

    Returns:
        A tuple of ``(agent, credential, client)`` so the caller can manage
        the async context lifetime.  Use the returned objects inside an
        ``async with`` block or call ``await credential.close()`` /
        ``await client.close()`` when done.

    Example usage from another file::

        from main import create_agent

        agent, credential, client = await create_agent()
        # ... use agent ...
        await client.close()
        await credential.close()
    """
    load_dotenv(override=False)

    project_endpoint = project_endpoint or os.getenv("PROJECT_ENDPOINT")
    model_deployment_name = model_deployment_name or os.getenv(
        "MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini"
    )

    credential = DefaultAzureCredential()
    client = AzureAIAgentClient(
        project_endpoint=project_endpoint,
        model_deployment_name=model_deployment_name,
        credential=credential,
    )

    agent = client.create_agent(
        name="math-solver",
        instructions=AGENT_INSTRUCTIONS,
        tools=MATH_TOOLS,
    )

    return agent, credential, client


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------

async def main():
    """Main function to run the agent as a web server."""
    logging.basicConfig(level=logging.INFO)

    agent, credential, client = create_agent()

    try:
        logger.info("Math Solver Agent Server running on http://localhost:8088")
        server = from_agent_framework(agent)
        await server.run_async()
    finally:
        await client.close()
        await credential.close()


if __name__ == "__main__":
    asyncio.run(main())