import re


def grade(sample, item):
    """Grade whether the agent response shows its work.

    Checks for:
    - Presence of a tool/function result (e.g., "Result:", "roots:", "GCD", "LCM", "Factorial")
    - Presence of an explanation or step-by-step reasoning
    - Mention of which tool was used

    Returns a score between 0.0 and 1.0.
    """
    response = sample.get("output_text", "")
    if not response:
        return 0.0

    score = 0.0

    # Check for tool output indicators (0.4 weight)
    tool_output_patterns = [
        r"Result:",
        r"roots?:",
        r"x\d?\s*=",
        r"GCD\(",
        r"LCM\(",
        r"\d+!\s*=",
        r"Mean:",
        r"Median:",
        r"Std Dev",
        r"0[xXbBoO][0-9a-fA-F]+",
    ]
    if any(re.search(p, response) for p in tool_output_patterns):
        score += 0.4

    # Check for explanation / reasoning (0.3 weight)
    explanation_patterns = [
        r"step",
        r"first|then|next|finally",
        r"because|since|therefore",
        r"we (get|have|find|compute|calculate|solve|use)",
        r"using the|applying",
        r"the (formula|equation|expression|discriminant)",
    ]
    if any(re.search(p, response, re.IGNORECASE) for p in explanation_patterns):
        score += 0.3

    # Check for tool attribution (0.3 weight)
    tool_names = [
        r"basic_arithmetic",
        r"solve_quadratic",
        r"compute_statistics",
        r"compute_factorial",
        r"compute_gcd_lcm",
        r"convert_base",
        r"tool",
        r"function",
    ]
    if any(re.search(p, response, re.IGNORECASE) for p in tool_names):
        score += 0.3

    return round(score, 2)
