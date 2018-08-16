#!/usr/bin/env python3

import argparse
import glob
import os
from task_maker.promise import ForkablePromise, UnionPromiseBuilder
from typing import Dict, List, Any, Tuple
from typing import Optional

import yaml

from task_maker.dependency_finder import find_dependency
from task_maker.language import grader_from_file, valid_extensions
from task_maker.sanitize import sanitize_command
from task_maker.source_file import from_file
from task_maker.formats import ScoreMode, Subtask, TestCase, Task, Dependency, GraderInfo, SourceFile, provide_file

VALIDATION_INPUT_NAME = "tm_input_file"


def list_files(patterns: List[str],
               exclude: Optional[List[str]] = None) -> List[str]:
    if exclude is None:
        exclude = []
    files = [_file for pattern in patterns
             for _file in glob.glob(pattern)]  # type: List[str]
    return [
        res
        for res in files
        if res not in exclude and os.path.splitext(res)[1] in valid_extensions()
    ]


def load_testcases() -> Tuple[Optional[str], Dict[int, Subtask]]:
    nums = [
        int(input_file[11:-4])
        for input_file in glob.glob(os.path.join("input", "input*.txt"))
    ]
    if not nums:
        raise RuntimeError("No generator and no input files found!")

    subtask = Subtask(ScoreMode.SUM, 100, {})

    for num in sorted(nums):
        testcase = TestCase(None, [], [], None, [], os.path.join("input", "input%d.txt" % num),
                            os.path.join("output", "output%d.txt" % num), get_write_input_file(num),
                            get_write_output_file(num))
        subtask.testcases[num] = testcase
    return None, {0: subtask}


def get_generator() -> Optional[str]:
    for generator in list_files(["gen/generator.*", "gen/generatore.*"]):
        return generator
    return None


def get_validator() -> Optional[str]:
    for validator in list_files(["gen/validator.*", "gen/valida.*"]):
        return validator
    return None


def get_official_solution() -> Optional[str]:
    for sol in list_files(["sol/solution.*", "sol/soluzione.*"]):
        return sol
    return None


def get_write_input_file(tc_num: int) -> str:
    return "input/input%d.txt" % tc_num


def get_write_output_file(tc_num: int) -> str:
    return "output/output%d.txt" % tc_num


def gen_testcases(
        copy_compiled: bool) -> Tuple[Optional[str], Dict[int, Subtask]]:
    subtasks = {}  # type: Dict[int, Subtask]

    def create_subtask(subtask_num: int, testcases: Dict[int, TestCase],
                       score: float) -> None:
        if testcases:
            subtask = Subtask(ScoreMode.MIN, score, {})
            for testcase_num, testcase in testcases.items():
                subtask.testcases[testcase_num] = testcase
            subtasks[subtask_num] = subtask

    generator = get_generator()
    if not generator:
        return load_testcases()
    validator = get_validator()
    if not validator:
        raise RuntimeError("No validator found")
    official_solution = get_official_solution()
    if official_solution is None:
        raise RuntimeError("No official solution found")

    current_testcases = {}  # type: Dict[int, TestCase]
    subtask_num = -1  # the first #ST line will skip a subtask!
    testcase_num = 0
    current_score = 0.0
    for line in open("gen/GEN"):
        testcase = TestCase(None, [], [], None, [], None, None, get_write_input_file(testcase_num),
                            get_write_output_file(testcase_num))
        if line.startswith("#ST: "):
            create_subtask(subtask_num, current_testcases, current_score)
            subtask_num += 1
            current_testcases = {}
            current_score = float(line.strip()[5:])
            continue
        elif line.startswith("#COPY: "):
            testcase.input_file = line[7:].strip()
        else:
            line = line.split("#")[0].strip()
            if not line:
                continue
            # a new testcase without subtask
            if subtask_num < 0:
                subtask_num = 0
            args = line.split()
            arg_deps = sanitize_command(args)
            testcase.generator = from_file(generator, copy_compiled and "bin/generator")
            testcase.generator_args.extend(args)
            testcase.extra_deps.extend(arg_deps)
            testcase.validator = from_file(validator, copy_compiled and "bin/validator")
            # in the old format the subtask number is 1-based
            testcase.validator_args.extend([VALIDATION_INPUT_NAME,
                                            str(subtask_num + 1)])
        current_testcases[testcase_num] = testcase
        testcase_num += 1

    create_subtask(subtask_num, current_testcases, current_score)
    # Hack for when subtasks are not specified.
    if len(subtasks) == 1 and subtasks[0].max_score == 0:
        subtasks[0].score_mode = ScoreMode.SUM
        subtasks[0].max_score = 100
    return official_solution, subtasks


def detect_yaml() -> str:
    cwd = os.getcwd()
    task_name = os.path.basename(cwd)
    yaml_names = ["task", os.path.join("..", task_name)]
    yaml_ext = ["yaml", "yml"]
    for name in yaml_names:
        for ext in yaml_ext:
            path = os.path.join(cwd, name + "." + ext)
            if os.path.exists(path):
                return path
    raise FileNotFoundError("Cannot find the task yaml of %s" % cwd)


def parse_task_yaml() -> Dict[str, Any]:
    path = detect_yaml()
    with open(path) as yaml_file:
        return yaml.load(yaml_file)


def get_options(data: Dict[str, Any],
                names: List[str],
                default: Optional[Any] = None) -> Any:
    for name in names:
        if name in data:
            return data[name]
    if not default:
        raise ValueError(
            "Non optional field %s missing from task.yaml" % "|".join(names))
    return default


def create_task_from_yaml(data: Dict[str, Any]) -> Task:
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["title", "nome"])
    if name is None:
        raise ValueError("The name is not set in the yaml")
    if title is None:
        raise ValueError("The title is not set in the yaml")

    time_limit = get_options(data, ["time_limit", "timeout"])
    memory_limit = get_options(data, ["memory_limit", "memlimit"]) * 1024
    input_file = get_options(data, ["infile"], "input.txt")
    output_file = get_options(data, ["outfile"], "output.txt")

    task = Task(name, title, {}, None, [], None, time_limit, memory_limit, input_file if input_file else "",
                output_file if output_file else "")
    return task


def get_solutions(solutions, graders) -> List[str]:
    if solutions:
        solutions = list_files([
            sol + "*" if sol.startswith("sol/") else "sol/" + sol + "*"
            for sol in solutions
        ])
    else:
        solutions = list_files(
            ["sol/*"], exclude=graders + ["sol/__init__.py"])
    return solutions


def get_checker() -> Optional[str]:
    checkers = list_files(["cor/checker.*", "cor/correttore.cpp"])
    if not checkers:
        checker = None
    elif len(checkers) == 1:
        checker = checkers[0]
    else:
        raise ValueError("Too many checkers in cor/ folder")
    return checker


def get_request(args: argparse.Namespace) -> (Task, List[SourceFile]):
    copy_compiled = args.copy_exe
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)

    graders = list_files(["sol/grader.*"])
    solutions = get_solutions(args.solutions, graders)
    checker = get_checker()

    grader_map = dict()

    for grader in graders:
        name = os.path.basename(grader)
        info = GraderInfo(grader_from_file(grader), [Dependency(name, grader)] + find_dependency(grader))
        grader_map[info.for_language] = info
        task.grader_info.extend([info])

    official_solution, subtasks = gen_testcases(copy_compiled)
    if official_solution:
        task.official_solution = from_file(official_solution, copy_compiled and "bin/official_solution",
                                           grader_map=grader_map)

    if checker is not None:
        task.checker = from_file(checker, copy_compiled and "bin/checker")
    for subtask_num, subtask in subtasks.items():
        task.subtasks[subtask_num] = subtask

    sols = []  # type: List[SourceFile]
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        bin_file = copy_compiled and "bin/" + path + "_" + ext[1:]
        sols.extend([from_file(solution, bin_file, grader_map=grader_map)])

    return task, sols


def evaluate_task(context, task: Task, solutions: List[SourceFile]):
    ins, outs, vals = generate_inputs(context, task)
    evaluate_solutions(context, task, ins, outs, vals, solutions)


def generate_inputs(context, task: Task) -> (
        Dict[int, ForkablePromise], Dict[int, ForkablePromise], Dict[int, ForkablePromise]):
    inputs = dict()
    outputs = dict()
    validations = dict()
    for st_num, subtask in task.subtasks.items():
        for tc_num, testcase in subtask.testcases.items():
            # input file
            if testcase.input_file:
                inputs[tc_num] = provide_file(context, testcase.input_file, "Static input %d" + tc_num, False)
            else:
                testcase.generator.prepare(context)
                testcase.validator.prepare(context)

                gen, gen_proms = testcase.generator.execute(context, "Generation of input %d" % tc_num,
                                                            testcase.generator_args)
                for dep in testcase.extra_deps:
                    prom = provide_file(context, dep.path, dep.path, False)
                    gen_proms.add(prom.then(lambda s: gen.addInput(dep.name, s.file)))
                # TODO set cache mode
                # TODO set limits?
                inputs[tc_num] = ForkablePromise(gen.stdout())
                gen_result = gen_proms.finalize().then(lambda: gen.getResult())
                # TODO write input file

                val, val_proms = testcase.validator.execute(context, "Validation of input %d" % tc_num,
                                                            testcase.validator_args)
                # TODO set cache mode
                # TODO set limits?
                val_proms.add(inputs[tc_num].then(lambda f: val.addInput(VALIDATION_INPUT_NAME, f.file)))
                validations[tc_num] = ForkablePromise(val.stdout())
                val_result = val_proms.finalize().then(lambda: val.getResult())

            # output file
            if testcase.output_file:
                outputs[tc_num] = provide_file(context, testcase.output_file, "Static output %d" % tc_num, False)
            else:
                task.official_solution.prepare(context)
                sol, sol_proms = task.official_solution.execute(context, "Generation of output %d" % tc_num, [])
                # TODO set cache mode
                # TODO set limits?

                if tc_num in validations:
                    sol_proms.add(validations[tc_num].then(lambda f: sol.addInput("wait_for_validation", f.file)))
                if task.input_file:
                    sol_proms.add(inputs[tc_num].then(lambda f: sol.addInput(task.input_file, f.file)))
                else:
                    sol_proms.add(inputs[tc_num].then(lambda f: sol.stdin(f.file)))
                if task.output_file:
                    outputs[tc_num] = ForkablePromise(sol.output(task.output_file, False))
                else:
                    outputs[tc_num] = ForkablePromise(sol.stdout(False))
                sol_result = sol_proms.finalize().then(lambda: sol.getResult())
                # TODO write output file
    return inputs, outputs, validations


def evaluate_solutions(context, task: Task, inputs: Dict[int, ForkablePromise], outputs: Dict[int, ForkablePromise],
                       validations: Dict[int, ForkablePromise], solutions: List[SourceFile]):
    for solution in solutions:
        solution.prepare(context)
        for tc_num, input in inputs.items():
            eval, eval_proms = solution.execute(context, "Evaluation of %s on testcase %d" % (solution.name, tc_num),
                                                [])
            # TODO set cache mode
            # TODO set limits!
            eval_proms.add(validations[tc_num].then(lambda f: f.file))
            if task.input_file:
                eval_proms.add(inputs[tc_num].then(lambda f: eval.addInput(task.input_file, f.file)))
            else:
                eval_proms.add(inputs[tc_num].then(lambda f: eval.stdin(f.file)))
            if task.output_file:
                output = ForkablePromise(eval.output(task.output_file, False))
            else:
                output = ForkablePromise(eval.stdout(False))
            eval_result = eval_proms.finalize().then(lambda: eval.getResult())

            if task.checker:
                task.checker.prepare(context)
                check, check_proms = task.checker.execute(context, "Checking solution %s for testcase %d" % (
                    solution.name, tc_num), ["input", "output", "contestant_output"])
                check_proms.add(inputs[tc_num].then(lambda f: check.addInput("input", f.file)))
            else:
                check = context.addExecution("Checking solution %s for testcase %d" % (solution.name, tc_num)).execution
                check.setExecutablePath("diff")
                check.setArgs(["-w", "output", "contestant_output"])
                check_proms = UnionPromiseBuilder()
            check_proms.add(outputs[tc_num].then(lambda f: check.addInput("output", f.file)))
            check_proms.add(output.then(lambda f: check.addInput("contestant_output", f.file)))
            # TODO set cache mode
            check_result = check_proms.finalize().then(lambda: check.getResult())

            # TODO calculate the status of the solution on this testcase and update the score


def clean():
    def remove_dir(path: str, pattern: str) -> None:
        if not os.path.exists(path):
            return
        for file in glob.glob(os.path.join(path, pattern)):
            os.remove(file)
        try:
            os.rmdir(path)
        except OSError:
            print("Directory %s not empty, kept non-%s files" % (path,
                                                                 pattern))

    def remove_file(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    if get_generator():
        remove_dir("input", "*.txt")
        remove_dir("output", "*.txt")
    remove_dir("bin", "*")
    remove_file(os.path.join("cor", "checker"))
    remove_file(os.path.join("cor", "correttore"))
