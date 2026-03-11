# Copyright (c) Microsoft. All rights reserved.

import os
from dotenv import load_dotenv
from pytest_agent_evals import (
    EvaluatorResults,
    evals,
    AzureOpenAIModelConfig,
    ChatAgentConfig,
    BuiltInEvaluatorConfig,
)
import pytest
from main import create_agent
from eval_utils import load_evaluator

load_dotenv()

# Configuration for the Evaluator (Judge)
# We use standard AOAI environment variables for the evaluator
EVAL_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
EVAL_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Load evaluator configs from YAML definitions
math_correctness_evaluator = load_evaluator("evaluators/math_correctness.yaml")
explanation_correctness_evaluator = load_evaluator("evaluators/explanation_correctness.yaml")

@pytest.fixture
def math_solver_agent():
    agent, _, _ = create_agent()
    return agent

# --- Tests ---

# The Test Class is the main entry point for defining your evaluation suite.
# We use decorators to configure the agent, dataset, and judge model.

@evals.dataset("../datasets/math-solver-test.jsonl")  # Specifies the input dataset file (JSONL format)
@evals.judge_model(AzureOpenAIModelConfig(deployment_name=EVAL_DEPLOYMENT, endpoint=EVAL_ENDPOINT)) # Configures the LLM used for "Judge" evaluators
@evals.agent(ChatAgentConfig(agent_fixture=math_solver_agent)) # Links this test class to the Chat agent
class Test_MathSolver:
    """
    Test class for the Agent: MathSolver.
    Each method represents a specific evaluation criteria (e.g., Relevance, Coherence).
    """
    @evals.evaluator(BuiltInEvaluatorConfig("task_adherence"))
    def test_task_adherence(self, evaluator_results: EvaluatorResults):
        """
        Tests the 'task_adherence' of the agent's response.
        The evaluator is automatically run and the results are populated to evaluator_results.<evaluator_name>
        """
        # Assert that the result is pass
        assert evaluator_results.task_adherence.result == "pass"


    @evals.evaluator(math_correctness_evaluator)
    def test_math_correctness(self, evaluator_results: EvaluatorResults):
        """
        Tests mathematical correctness using a custom prompt template
        loaded from evaluators/math_correctness.yaml.
        """
        assert evaluator_results.math_correctness.result == "pass"

    @evals.evaluator(explanation_correctness_evaluator)
    def test_explanation_correctness(self, evaluator_results: EvaluatorResults):
        """
        Tests that the agent shows its work (tool output + explanation)
        using a custom code evaluator loaded from evaluators/explanation_correctness.yaml.
        """
        assert evaluator_results.explanation_correctness.result == "pass"
