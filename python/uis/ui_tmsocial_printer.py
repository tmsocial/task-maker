#!/usr/bin/env python3

import json

from typing import Dict


class UITMSocialPrinter:
    """
    This class will manage the printing to the console, whether if it's text
    based or json
    """

    def testcase_outcome(self, solution: str, testcase: int, subtask: int,
                         info: "TestcaseSolutionInfo"):
        base_key = f"subtask.{subtask}.testcase.{testcase}"
        self.value_event(key=f"{base_key}.status", value=str(info.status).split(".")[-1])
        self.value_event(key=f"{base_key}.message", value=info.message)
        self.value_event(key=f"{base_key}.score", value=info.score)
        self.value_event(key=f"{base_key}.error", value=info.result[0].error)
        self.value_event(key=f"{base_key}.was_killed", value=info.result[0].was_killed)
        self.value_event(key=f"{base_key}.return_code", value=info.result[0].return_code if info.result[0].was_killed else 0)
        self.value_event(key=f"{base_key}.time_usage", value=info.result[0].resources.cpu_time)
        self.value_event(key=f"{base_key}.memory_usage", value=info.result[0].resources.memory)
        self.value_event(key=f"{base_key}.signal", value=info.result[0].signal if info.result[0].was_killed else None)

    def subtask_outcome(self, solution: str, subtask: int,
                        result: "SubtaskSolutionResult", score: float):
        self.value_event(key=f"subtask.{subtask}.status", value=result.value)
        self.value_event(key=f"subtask.{subtask}.score", value=score)

    def warning(self, message: str):
        self.print(message, "warning", "WARNING", {"message": message})

    def error(self, message: str):
        self.print(message, "error", "ERROR", {"message": message})

    @staticmethod
    def print(name: str, tag: str, state: str, data: Dict):
        print(json.dumps({
            "type": "task-maker",
            "tag": tag,
            "name": name,
            "state": state,
            "data": data,
        }), flush=True)

    @staticmethod
    def value_event(*, key: str, value: object):
        print(json.dumps({
            "type": "value",
            "key": key,
            "value": value,
        }), flush=True)
