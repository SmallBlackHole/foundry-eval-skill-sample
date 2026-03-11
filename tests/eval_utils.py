"""Utility for loading evaluator YAML definitions as pytest-agent-evals configs."""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Union

import yaml
from pytest_agent_evals import CustomCodeEvaluatorConfig, CustomPromptEvaluatorConfig


def load_evaluator(
    yaml_path: str,
) -> Union[CustomPromptEvaluatorConfig, CustomCodeEvaluatorConfig]:
    """Load an evaluator YAML file and return the matching evaluator config.

    The YAML file must contain at least ``name`` and ``pass_threshold``, plus
    one of:

    * ``prompt_text`` – returns a :class:`CustomPromptEvaluatorConfig`
    * ``code_path``   – returns a :class:`CustomCodeEvaluatorConfig`
      (the referenced Python file must define a top-level ``grade`` function)

    Args:
        yaml_path: Path to the evaluator YAML file (absolute or relative to
                   the workspace root).

    Returns:
        A ``CustomPromptEvaluatorConfig`` or ``CustomCodeEvaluatorConfig``
        ready to pass to ``@evals.evaluator()``.
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.is_absolute():
        # Resolve relative to the project root (parent of tests/)
        yaml_path = Path(__file__).resolve().parent.parent / yaml_path

    with open(yaml_path, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)

    name: str = spec["name"]
    threshold = spec["pass_threshold"]

    if "prompt_text" in spec:
        return CustomPromptEvaluatorConfig(
            name=name,
            prompt=spec["prompt_text"],
            threshold=threshold,
        )

    if "code_path" in spec:
        code_path = Path(spec["code_path"])
        if not code_path.is_absolute():
            code_path = yaml_path.parent.parent / code_path

        # Dynamically import the grader module and extract `grade`
        module_name = f"_evaluator_{name}"
        module_spec = importlib.util.spec_from_file_location(module_name, code_path)
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)

        if not hasattr(module, "grade"):
            raise AttributeError(
                f"Evaluator code at '{code_path}' must define a top-level 'grade' function."
            )

        return CustomCodeEvaluatorConfig(
            name=name,
            grader=module.grade,
            threshold=threshold,
        )

    raise ValueError(
        f"Evaluator YAML '{yaml_path}' must contain either 'prompt_text' or 'code_path'."
    )
