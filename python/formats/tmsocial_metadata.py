# from statement import generate_statement

from task_maker.formats import IOITask, Subtask

import os
import base64


LANGUAGE_MAP = {
    "italian.pdf": "it",
    "english.pdf": "en",
}


def load_pdf_statement(path):
    with open(path, "rb") as f:
        return base64.encodebytes(f.read()).decode()


def generate_statement(*, task_dir: str):
    pdf_base64 = {
        LANGUAGE_MAP[path]: load_pdf_statement(
            os.path.join(task_dir, sub_dir, path))
        for sub_dir in ["statement", "testo"]
        if os.path.isdir(os.path.join(task_dir, sub_dir))
        for path in os.listdir(os.path.join(task_dir, sub_dir))
        if path in LANGUAGE_MAP
    }

    if len(pdf_base64) == 0:
        pdf_base64 = None

    return dict(
        pdf_base64=pdf_base64,
    )


def gen_path(subtask: int, testcase: int, field: str):
    return f"subtask.{subtask}.testcase.{testcase}.{field}"


def generate_cells(subtask_index: int, testcase_index: int):
    yield dict(number=testcase_index)
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "status")))
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "memory_usage")))
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "time_usage")))
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "signal")))
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "return_code")))
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "message")))
    yield dict(value=dict(type="ref", ref=gen_path(subtask_index, testcase_index, "score")))


def generate_testcases(index: int, subtask: Subtask):
    for testcase_index, testcase in subtask.testcases.items():
        yield dict(title=f"Test case {index}", cells=list(generate_cells(index, testcase_index)))


def generate_subtasks(task: IOITask):
    for index, subtask in task.subtasks.items():
        yield dict(max_score=subtask.max_score, title=f"Subtask {index}", rows=list(generate_testcases(index, subtask)))


def generate_table(task: IOITask):
    return dict(
        type="table",
        columns=[
            dict(type="row_number", name=dict(default="Test Case")),
            dict(type="row_status"),
            dict(type="memory_usage", name=dict(default="Memory Usage")),
            dict(type="time_usage", name=dict(default="Time Usage")),
            dict(type="signal", name=dict(default="Exit signal")),
            dict(type="return_code", name=dict(default="Return code")),
            dict(type="message", name=dict(default="Message")),
            dict(type="score", name=dict(default="Score")),
        ],
        groups=list(generate_subtasks(task)),
    )


def generate_metadata(task: IOITask, task_dir: str):
    return dict(
        title=dict(default=task.title),
        statement=generate_statement(task_dir=task_dir),
        submission_form=dict(fields=[
            dict(id="solution", title=dict(default="Solution"), types=[
                dict(id="cpp", title=dict(default="C++"), extensions=[".cpp", ".cc"]),
                dict(id="pas", title=dict(default="Pascal"), extensions=[".pas"]),
                dict(id="python3.py", title=dict(default="Python 3"), extensions=[".py"]),
                dict(id="python2.py", title=dict(default="Python 2"), extensions=[".py"]),
            ], required=True)
        ]),
        evaluation_sections=[
            generate_table(task),
        ],
        task_maker_info=task.to_dict(),
    )
