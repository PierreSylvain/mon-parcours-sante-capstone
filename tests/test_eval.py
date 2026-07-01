# tests/test_eval.py
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
async def test_functional():
    await AgentEvaluator.evaluate(
        agent_module="mon_parcours_sante",
        eval_dataset_file_path_or_dir="evals/functional",
        num_runs=5,
    )
