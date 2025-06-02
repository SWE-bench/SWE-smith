"""
Utility functions for transforming SWE-agent trajectories to fine-tuning format.
"""

import json
import yaml

XML_STR_REPLACES = ["old_str", "new_str", "file_text"]


# TODO: Fix this, this is hardcoded, so will break if not called from root of a directory
SYSTEM_PROMPT = yaml.safe_load(open("agent/swesmith_infer.yaml", "r"))["agent"][
    "templates"
]["system_template"]


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


def transform_traj_xml(traj: dict) -> dict:
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
                action = "\n".join(tool_call_to_action(message["tool_calls"]))
                content = f"{message['thought']}\n\n{action}"
        elif message["role"] == "system":
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


MAP_STYLE_TO_FUNC = {"ticks": transform_traj_backticks, "xml": transform_traj_xml}
