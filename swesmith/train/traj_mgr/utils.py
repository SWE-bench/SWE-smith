"""
Utility functions for transforming SWE-agent trajectories to fine-tuning format.
"""

import json
import yaml

from swesmith import REPO_DIR

XML_STR_REPLACES = ["old_str", "new_str", "file_text"]


SYSTEM_PROMPT = yaml.safe_load(
    (REPO_DIR / "agent" / "swesmith_infer.yaml").read_text()
)["agent"]["templates"]["system_template"]


def get_messages(traj: dict) -> list[dict]:
    """Extract messages from a swe-agent trajectory.

    We assume that the messages of the last step correspond to the
    full message history.
    This is a bit of an approximation (e.g., requeries after blocked actions
    aren't fully captured)
    """
    last_step = traj["trajectory"][-1]
    # There was a change in output formats in swe-agent 1.1.0:
    # https://swe-agent.com/latest/usage/trajectories/
    # For < 1.1.0, we had the 'messages' field that included messages
    # _after_ the message was performed (and then we remove the last message because
    # it contains the submit/patch)
    # For >= 1.1.0, we have the 'query' field that includes messages that were the
    # direct input to the agent at that step (so do not need to exclude the last message)
    if "messages" in last_step:
        return last_step["messages"][:-1]
    else:
        if last_step["response"] in [
            "Exit due to cost limit",
            "Exit due to context window",
        ]:
            return traj["trajectory"][-2]["query"][:]
        return last_step["query"][:]


def transform_traj_backticks(traj: dict) -> dict:
    """Transform a swe-agent trajectory to backticks format, i.e.,
    for use with the `thought-action` parser of swe-agent where actions
    are extracted from triple-backticks blocks.
    """
    new_traj = []
    for message in get_messages(traj):
        role = message["role"] if message["role"] != "tool" else "user"
        if message["role"] == "assistant":
            content = f"{message['thought']}\n\n```\n{message['action']}\n```"
        elif message["role"] == "system":
            content = message["content"]
        else:
            assert len(message["content"]) == 1
            content = message["content"][0]["text"]
        new_traj.append({"role": role, "content": content})
    return {"messages": new_traj}


def tool_call_to_action(tool_calls: None | list[dict]) -> list[str]:
    actions = []
    if tool_calls is None:
        return []
    for tool_call in tool_calls:
        action = [f"<function={tool_call['function']['name']}>"]
        arguments = json.loads(tool_call["function"]["arguments"])
        for k, v in arguments.items():
            a = f"<parameter={k}>{v}</parameter>"
            if k in XML_STR_REPLACES:
                a = f"<parameter={k}>\n{v}\n</parameter>"
            action.append(a)
        action.append("</function>")
        actions.append("\n".join(action))
    return actions


def transform_traj_xml(traj: dict) -> dict:
    new_traj = []
    for message in get_messages(traj):
        role = message["role"] if message["role"] != "tool" else "user"
        if message["role"] == "assistant":
            if message["content"] == "Exit due to cost limit":
                content = (
                    "Since we have successfully fixed the issue and verified it works, "
                    + "let's submit the changes:\n\n"
                    + "<function=submit>\n</function>"
                )
            else:
                content = message.get("thought", message["content"])
                if "tool_calls" in message:
                    action = "\n".join(tool_call_to_action(message["tool_calls"]))
                    content += f"\n\n{action}"
                content = content.strip()
        elif message["role"] == "system":
            # We replace the system prompt that was used for generating the training trajectories
            # with the system prompt that SWE-agent-LM will use for inference.
            content = SYSTEM_PROMPT
        else:
            if isinstance(message["content"], list):
                assert len(message["content"]) == 1
                content = message["content"][0]["text"]
            elif isinstance(message["content"], str):
                content = message["content"]
            else:
                raise ValueError(f"Message type not recognized: {type(message)}")
        new_traj.append({"role": role, "content": content})
    return {"messages": new_traj}


def transform_traj_toolcalls(traj: dict) -> dict:
    return {"messages": get_messages(traj)}


MAP_STYLE_TO_FUNC = {
    "ticks": transform_traj_backticks,
    "tool": transform_traj_toolcalls,
    "xml": transform_traj_xml,
}
