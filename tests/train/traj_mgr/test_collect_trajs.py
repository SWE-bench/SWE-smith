import json
import os
import tempfile

from pathlib import Path
from swesmith.train.traj_mgr.collect_trajs import main as collect_trajs
from swesmith.train.traj_mgr.utils import transform_traj_xml


def test_transform_traj_xml_basic(
    logs_trajectories, logs_run_evaluation, ft_xml_example
):
    # Load a sample trajectory
    for inst_id in [
        "getmoto__moto.694ce1f4.pr_7331",
        "pandas-dev__pandas.95280573.pr_53652",
        "pydantic__pydantic.acb0f10f.pr_8316",
    ]:
        traj_path = logs_trajectories / inst_id / f"{inst_id}.traj"
        report_path = logs_run_evaluation / inst_id / "report.json"

        with open(traj_path, "r") as f:
            traj_data = json.load(f)

        # Transform the trajectory
        transformed = transform_traj_xml(traj_data)

        # Basic structure checks
        assert "messages" in transformed
        assert isinstance(transformed["messages"], list)
        assert len(transformed["messages"]) > 0

        # Check each message has required fields
        for msg in transformed["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["system", "user", "assistant"]

            # For assistant messages, check XML structure
            if msg["role"] == "assistant":
                content = msg["content"]
                # If it's a function call (action), check XML structure
                if "<function=" in content:
                    assert "</function>" in content
                    action_body = content.split("<function=")[1].split("</function>")[0]
                    # Check parameter structure if present
                    if "<parameter=" in action_body:
                        assert "</parameter>" in action_body

        # Add `resolved` status
        with open(report_path) as f:
            report = json.load(f)
        with open(ft_xml_example, "r") as f:
            expected = [
                json.loads(x) for x in f if json.loads(x)["instance_id"] == inst_id
            ][0]
        transformed["resolved"] = report["resolved"]
        transformed["instance_id"] = inst_id
        transformed["model"] = json.loads(traj_data["replay_config"])["agent"]["model"][
            "name"
        ]
        del expected["traj_id"]
        del expected["patch"]
        assert transformed == expected


def test_collect_trajs_basic(logs_trajectories, logs_run_evaluation, ft_xml_example):
    with tempfile.TemporaryDirectory() as tmpdir:
        collect_trajs(
            Path(tmpdir),
            logs_trajectories,
            logs_run_evaluation,
            style="xml",
            workers=4,
        )

        # Check that the output file exists
        expected_file_path = f"{os.path.basename(logs_run_evaluation)}.xml.jsonl"
        output_path = Path(tmpdir) / expected_file_path
        assert output_path.exists()

        # Compare contents
        output_data = []
        with open(output_path, "r") as f:
            for x in f:
                traj = json.loads(x)
                del traj["traj_id"]
                output_data.append(traj)
        expected_data = []
        with open(ft_xml_example, "r") as f:
            for x in f:
                traj = json.loads(x)
                del traj["traj_id"]
                expected_data.append(traj)

        assert sorted(output_data, key=lambda x: x["instance_id"]) == sorted(
            expected_data, key=lambda x: x["instance_id"]
        )

        # Remove the output file
        output_path.unlink()
