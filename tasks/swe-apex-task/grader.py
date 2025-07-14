import subprocess

from apex_arena._types import GradingResult


def grade(transcript: str) -> GradingResult:
    """Grade the MonkeyType task by running pytest."""

    subscores = {"pytest": 0.0}

    feedback_parts = []

    try:
        result = subprocess.run(
            ["bash", "-c", "source /opt/miniconda3/etc/profile.d/conda.sh && conda activate testbed && /workdir/run_test.sh"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            subscores["pytest"] = 1.0
            feedback_parts.append("✓ pytest passed")
        else:
            subscores["pytest"] = 0.0
            feedback_parts.append(f"✗ pytest failed: {result.stderr} || {result.stdout}")

    except subprocess.TimeoutExpired:
        feedback_parts.append("✗ pytest timed out")
    except Exception as e:
        feedback_parts.append(f"✗ Error running pytest: {str(e)}")

    weights = {"pytest": 1.0}

    total_score = sum(subscores[key] * weights[key] for key in subscores)

    return GradingResult(
        score=total_score,
        subscores=subscores,
        weights=weights,
        feedback=" | ".join(feedback_parts).replace("[", "").replace("]", ""),
    )