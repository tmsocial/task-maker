#!/usr/bin/env python3

import json

from typing import Dict



class UITMSocialPrinter:
    """
    This class will manage the printing to the console, whether if it's text
    based or json
    """
    @staticmethod
    def get_testcase_result(result):
        from task_maker.uis.ioi import TestcaseSolutionStatus

        TESTCASE_RESULT_MAP = {
            TestcaseSolutionStatus.ACCEPTED: "success",
            TestcaseSolutionStatus.WRONG_ANSWER: "fail",
            TestcaseSolutionStatus.PARTIAL: "partial",
            TestcaseSolutionStatus.FAILED: "fail",
            TestcaseSolutionStatus.SKIPPED: "skip",
        }

        return TESTCASE_RESULT_MAP.get(result, result)

    @staticmethod
    def get_subtask_result(result):
        from task_maker.uis.ioi import SubtaskSolutionResult

        SUBTASK_RESULT_MAP = {
            SubtaskSolutionResult.ACCEPTED: "success",
            SubtaskSolutionResult.PARTIAL: "partial",
            SubtaskSolutionResult.REJECTED: "fail",
        }

        return SUBTASK_RESULT_MAP.get(result, result)

    def testcase_outcome(self, solution: str, testcase: int, subtask: int,
                         info: "TestcaseSolutionInfo"):
        base_key = f"subtask.{subtask}.testcase.{testcase}"
        self.value_event(key=f"{base_key}.status", value=dict(type="status", status=self.get_testcase_result(info.status)))
        self.value_event(key=f"{base_key}.message", value=dict(type="message", message=dict(default=info.message)))
        self.value_event(key=f"{base_key}.score", value=dict(type="score", score=info.score))
        self.value_event(key=f"{base_key}.time_usage", value=dict(type="time_usage", time_usage_seconds=info.result[0].resources.cpu_time))
        self.value_event(key=f"{base_key}.memory_usage", value=dict(type="memory_usage", memory_usage_bytes=info.result[0].resources.memory * 1024))
        self.value_event(key=f"{base_key}.error", value=info.result[0].error)
        self.value_event(key=f"{base_key}.was_killed", value=info.result[0].was_killed)
        self.value_event(key=f"{base_key}.return_code", value=info.result[0].return_code if info.result[0].was_killed else 0)
        self.value_event(key=f"{base_key}.signal", value=info.result[0].signal if info.result[0].was_killed else None)

    def subtask_outcome(self, solution: str, subtask: int,
                        result: "SubtaskSolutionResult", score: float):
        self.value_event(key=f"subtask.{subtask}.status", value=dict(type="status", status=self.get_subtask_result(result)))
        self.value_event(key=f"subtask.{subtask}.score", value=dict(type="score", score=score))

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
