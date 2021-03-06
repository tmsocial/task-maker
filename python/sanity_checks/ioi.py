#!/usr/bin/env python3

import os.path
import re
import subprocess
from distutils.spawn import find_executable
from task_maker.formats import IOITask, list_files, VALIDATION_INPUT_NAME, \
    TaskType
from task_maker.languages import Language
from task_maker.remote import ExecutionPool, Execution
from task_maker.solution import Solution, get_checker_execution
from task_maker.task_maker_frontend import File, Result, ResultStatus
from task_maker.uis.ioi import IOIUIInterface
from typing import List, Set, Optional, Dict


def _get_languages(solutions: List[Solution]):
    languages = set()
    for solution in solutions:
        languages.add(solution.solution.language)
    return languages


def _has_grader(solutions: List[Solution]):
    return any(sol.solution.grader for sol in solutions)


def _check_graders(folder: str, languages: Set[Language],
                   solutions: List[Solution], interface: IOIUIInterface):
    # if there is at least a grader assume the task is with graders
    if _has_grader(solutions):
        for language in languages:
            if not os.path.exists(folder + "grader" +
                                  language.source_extension):
                interface.add_warning("Missing grader{} in {} folder".format(
                    language.source_extension, folder))


def _get_statement_path():
    for path in ["statement/statement.pdf", "testo/testo.pdf"]:
        if os.path.lexists(path):
            return path
    return None


def _get_statement_tex():
    return list_files(["statement/*.tex", "testo/*.tex"],
                      valid_extensions=[".tex"])


def _check_git_has_file(path: str) -> Optional[bool]:
    # git is not installed
    if not find_executable("git"):
        return None
    proc = subprocess.run(["git", "ls-files", "--", path],
                          stderr=subprocess.DEVNULL,
                          stdout=subprocess.PIPE)
    # this is not a git repository
    if proc.returncode != 0:
        return None
    if proc.stdout.decode():
        return True
    return False


def _check_pdf_statement(interface: IOIUIInterface):
    path = _get_statement_path()
    if not path:
        interface.add_warning("The statement file is missing")
        return
    if _check_git_has_file(path) is False:
        interface.add_warning(
            "The statement file {} is not known to git".format(path))
    if os.path.islink(path):
        realpath = os.path.relpath(path)
        if not os.path.exists(realpath):
            interface.add_warning("The statement is a broken link")


def _check_tex_statement(task: IOITask, interface: IOIUIInterface):
    statements = _get_statement_tex()
    if not statements:
        return

    def check_oii_format(statement, content):
        regex = r".*\{Subtask ([0-9]+)\} *\[(?:\\phantom\{.\})?([0-9]+).*\].*"
        is_non_sequential = False
        is_wrong = False
        matches = re.findall(regex, content)
        if not matches:
            return
        one_based = int(matches[0][0] == '1')
        last = -1
        for subtask, score in matches:
            subtask = int(subtask) - one_based
            score = int(score)
            if subtask != last + 1:
                is_non_sequential = True
                # if the numbers are screwed up the scores have no sense
                break
            last = subtask
            from_task = task.subtasks.get(subtask)
            if not from_task or from_task.max_score != score:
                is_wrong = True
        if is_non_sequential:
            interface.add_warning(
                "The subtasks in the statement {} are "
                "non-sequentially numbered".format(statement))
        elif is_wrong:
            interface.add_warning(
                "The subtasks in the statement {} don't match "
                "the task's ones".format(statement))

    def check_ois_format(statement, content):
        regex = r".*\\OISubtask\{(\d+)\}\{\d+\}\{.+\}.*"
        matches = re.findall(regex, content)
        if not matches:
            return
        is_wrong = False
        if len(matches) != len(task.subtasks):
            is_wrong = True
        for score, subtask in zip(matches, task.subtasks.values()):
            if score != subtask.max_score:
                is_wrong = True
        if is_wrong:
            interface.add_warning(
                "The subtasks in the statement {} don't match "
                "the task's ones".format(statement))

    for statement in statements:
        with open(statement, "r") as f:
            content = f.read()
            check_oii_format(statement, content)
            check_ois_format(statement, content)


def _setup_execution_callback(interface: IOIUIInterface, execution: Execution,
                              error_message: str):
    def on_done(result: Result):
        if result.status != ResultStatus.SUCCESS:
            interface.add_error(error_message)

    execution.bind(on_done)


def _setup_checker_callback(interface: IOIUIInterface, checking: Execution,
                            error_message: str, custom_checker: bool):
    def on_done(result: Result):
        if result.status != ResultStatus.SUCCESS:
            interface.add_error(error_message)
        if not custom_checker:
            return
        stdout = checking.stdout_content
        try:
            score = float(stdout)
        except ValueError:
            interface.add_error(error_message +
                                ": invalid score: {}".format(stdout))
            return
        if not 0.0 <= score <= 1.0:
            interface.add_error(error_message +
                                ": invalid score: {}".format(stdout))
            return

    checking.bind(on_done)


def check_att_folder(task: IOITask, solutions: List[Solution],
                     interface: IOIUIInterface):
    """
    Check if the following files are present:
    - grader.* for all the languages which have a solution
    - task_name.* for all the languages above
    - task_name.inputX.txt / task_name.outputX.txt / inputX.txt / outputX.txt
      making sure that they are symlinks
    """
    languages = _get_languages(solutions)
    _check_graders("att/", languages, solutions, interface)
    if _has_grader(solutions):
        for language in languages:
            if not os.path.exists("att/{}{}".format(
                    task.name, language.source_extension)):
                interface.add_warning("Missing {}{} in att/ folder".format(
                    task.name, language.source_extension))
    sample_files = list_files([
        "att/input*.txt", "att/output*.txt", "att/{}.input*.txt".format(
            task.name), "att/{}.output*.txt".format(task.name)
    ])
    for sample in sample_files:
        if not os.path.islink(sample):
            interface.add_warning(
                "Sample file {} is not a symlink".format(sample))
    if len(sample_files):
        interface.add_warning("No sample files provided")


def check_sol_folder(solutions: List[Solution], interface: IOIUIInterface):
    """
    Check if the following files are present:
    - grader.* for all the languages which have a solution
    - solution.* / soluzione.cpp is a symlink
    """
    languages = _get_languages(solutions)
    _check_graders("sol/", languages, solutions, interface)
    sols = list_files(["sol/solution.*", "sol/soluzione.*"])
    if len(sols) > 1:
        interface.add_warning("More than one official solution found")
    for sol in sols:
        if not os.path.islink(sol):
            interface.add_warning(
                "Official solution {} is not a symlink".format(sol))


def check_statement(task: IOITask, interface: IOIUIInterface):
    """
    Check if the statement is present and, if git is used, that is known.
    Check that the latex statements, if present contain the same subtasks, with
    the same score, as the task
    Check if the template functions in the statement and in the graders have the
    same signature
    """
    _check_pdf_statement(interface)
    _check_tex_statement(task, interface)
    # TODO check if the template signatures match the one in the statement


def check_sample_cases(task: IOITask, pool: ExecutionPool,
                       interface: IOIUIInterface):
    """
    Check if the sample cases in the statement are valid and the output is
    correct
    """
    # Communication tasks does not have output files
    if task.task_type != TaskType.Batch:
        return

    # without official solution we cannot solve the input files
    if not task.official_solution:
        return

    inputs = list_files([
        "statement/input*.txt", "statement/{}.input*.txt".format(task.name),
        "testo/input*.txt", "testo/{}.input*.txt".format(task.name)
    ],
                        valid_extensions=[".txt"])
    outputs = list_files([
        "statement/output*.txt", "statement/{}.output*.txt".format(task.name),
        "testo/output*.txt", "testo/{}.output*.txt".format(task.name)
    ],
                         valid_extensions=[".txt"])
    num_to_input = dict()  # type: Dict[int, str]
    num_to_output = dict()  # type: Dict[int, str]
    num_to_input_file = dict()  # type: Dict[int, File]
    num_to_output_file = dict()  # type: Dict[int, File]
    num_to_sol_output_file = dict()  # type: Dict[int, File]
    num_to_validation = dict()  # type: Dict[int, File]

    for infile in inputs:
        match = re.match(r".*input(\d+).txt", infile)
        # invalid sample file format, skip it
        if not match:
            continue
        sample_num = int(match.group(1))
        num_to_input[sample_num] = infile
        num_to_input_file[sample_num] = pool.frontend.provideFile(
            infile, "Sample input {}".format(infile), False)
        # skip the validation if there is no default validator
        if not task.default_val:
            continue
        in_files = {VALIDATION_INPUT_NAME: num_to_input_file[sample_num]}
        validation = Execution(
            "Validation of sample input {}".format(infile),
            pool,
            task.default_val.source_file, [VALIDATION_INPUT_NAME, "0"],
            "sanity-check-validation", {
                "sample_testcase": sample_num
            },
            inputs=in_files)
        num_to_validation[sample_num] = validation.stdout
        _setup_execution_callback(
            interface, validation,
            "Validation of sample input {} failed".format(infile))

    # if the output files were not yet generated (e.g. when they are just
    # copied), the solution is not prepared
    if not task.official_solution.prepared:
        task.official_solution.prepare(pool)

    for outfile in outputs:
        match = re.match(r".*output(\d+).txt", outfile)
        if not match:
            continue
        sample_num = int(match.group(1))
        # skip the output if there is no corresponding input
        if sample_num not in num_to_input:
            continue
        num_to_output[sample_num] = outfile
        num_to_output_file[sample_num] = pool.frontend.provideFile(
            outfile, "Sample output {}".format(outfile), False)
        in_files = dict()
        # if the validator is not present we don't wait for it
        if sample_num in num_to_validation:
            in_files["wait_for_validation"] = num_to_validation[sample_num]
        if task.input_file:
            in_files[task.input_file] = num_to_input_file[sample_num]
            stdin = None
        else:
            stdin = num_to_input_file[sample_num]
        out_files = []
        if task.output_file:
            out_files.append(task.output_file)

        solving = Execution(
            "Solving sample output {}".format(outfile),
            pool,
            task.official_solution, [],
            "sanity-check-solution", {
                "sample_testcase": sample_num
            },
            inputs=in_files,
            stdin=stdin,
            outputs=out_files)
        if task.output_file:
            num_to_sol_output_file[sample_num] = solving.output(
                task.output_file)
        else:
            num_to_sol_output_file[sample_num] = solving.stdout

        _setup_execution_callback(
            interface, solving, "Solution of sample input {} failed".format(
                num_to_input[sample_num]))

        check = get_checker_execution(
            pool, task, "", -1, sample_num, task.checker,
            num_to_input_file[sample_num], num_to_output_file[sample_num],
            num_to_sol_output_file[sample_num],
            "Checking sample output {}".format(outfile),
            {"sanity_check": True})

        _setup_checker_callback(
            interface, check,
            "Checking sample output {} failed".format(outfile),
            task.checker is not None)


def check_solution_score(task: IOITask, interface: IOIUIInterface):
    """
    Check if the official solution scores full score
    """
    if not task.official_solution:
        return
    official_solution_name = task.official_solution.name
    if official_solution_name not in interface.testing:
        return
    max_score = sum(st.max_score for st in task.subtasks.values())
    if interface.testing[official_solution_name].score != max_score:
        interface.add_warning(
            "The official solution {} does not score full score".format(
                official_solution_name))


def check_subtask_score_sum(task: IOITask, interface: IOIUIInterface):
    """
    Check if the sum of the subtask max_score is 100
    """
    if sum(st.max_score for st in task.subtasks.values()) != 100:
        interface.add_warning("The sum of the subtask max scores is not 100")


def check_symlinks(interface: IOIUIInterface):
    """
    Check if there are broken symlinks in the task folders
    """
    dirs_to_check = ["att", "sol", "gen", "check", "cor", "statement", "testo"]
    for d in dirs_to_check:
        for root, dirs, files in os.walk(d):
            for f in files:
                f = os.path.join(root, f)
                if os.path.islink(f):
                    dest = os.path.join(os.path.dirname(f), os.readlink(f))
                    if not os.path.exists(dest):
                        interface.add_warning(
                            "Broken symlink: {} -> {}".format(f, dest))


def sanity_pre_checks(task: IOITask, solutions: List[Solution],
                      pool: ExecutionPool, interface: IOIUIInterface):
    """
    Runs all the checks that should be run before the execution of the task.
    """
    check_subtask_score_sum(task, interface)
    check_att_folder(task, solutions, interface)
    check_sol_folder(solutions, interface)
    check_sample_cases(task, pool, interface)


def sanity_post_checks(task: IOITask, solutions: List[Solution],
                       interface: IOIUIInterface):
    """
    Runs all the checks that should be run after the execution of the task.
    """
    check_solution_score(task, interface)
    check_statement(task, interface)
    check_symlinks(interface)
