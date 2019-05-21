#!/usr/bin/env python3
import json

from task_maker.printer import Printer
from typing import Dict


class UIPrinter:
    """
    This class will manage the printing to the console, whether if it's text
    based or json
    """

    def __init__(self, printer: Printer, json: bool):
        self.printer = printer
        self.json = json

    def testcase_outcome(self, solution: str, testcase: int, subtask: int, info: "TestcaseSolutionInfo"):
        self.print(
            f"Solution {solution} on testcase {testcase} scored {info.score:.2f}",
            "testcase-outcome",
            "SUCCESS",
            {
                "name": solution,
                "testcase": testcase,
                "subtask": subtask,
                "status": str(info.status).split(".")[-1],
                "score": info.score,
                "message": info.message,
            }
        )

    def subtask_outcome(self, solution: str, subtask: int, result: "SubtaskSolutionResult", score: float):
        self.print(
            f"Solution {solution} on subtask {subtask} scored {score:.2f}",
            "subtask-outcome",
            "SUCCESS",
            {
                "name": solution,
                "subtask": subtask,
                "status": str(result).split(".")[-1],
                "score": score,
            }
        )

    def terry_solution_outcome(self, solution: str, info: "SolutionInfo"):
        self.print(
            f"Outcome of solution {solution}: score={info.score} message={info.message}",
            "terry-solution-outcome",
            "SUCCESS",
            {
                "name": solution,
                "status": str(info.status).split(".")[-1],
                "score": info.score,
                "message": info.message,
                "testcases":
                    [str(s).split(".")[-1] for s in info.testcases_status]
            }
        )

    def warning(self, message: str):
        self.print(message, "warning", "WARNING", {"message": message})

    def error(self, message: str):
        self.print(message, "error", "ERROR", {"message": message})

    def print(self, name: str, tag: str, state: str, data: Dict[str, object]):
        if self.json:
            print(json.dumps({
                "action": tag,
                "state": state.upper(),
                "data": data
            }), flush=True)
        else:
            name = (name + " ").ljust(50) + state
            if "result" in data and data["result"]["was_cached"]:
                name += " [cached]"
            if state == "WAITING":
                self.printer.text("{name}\n")
            elif state == "SKIPPED":
                self.printer.yellow(f"{name}\n")
            elif state == "START":
                self.printer.text(f"{name}\n")
            elif state == "SUCCESS":
                self.printer.green(f"{name}\n")
            elif state == "WARNING":
                self.printer.yellow(f"{name} {data}\n")
            elif state == "FAILURE" or state == "ERROR":
                self.printer.red(f"{name} {data}\n")
            else:
                raise ValueError(f"Unknown state {state}")
