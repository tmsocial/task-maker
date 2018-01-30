#!/usr/bin/env python3

from tests.test import run_tests, TestingUI
from tests.utils import TestInterface


def test_task():
    interface = TestInterface("with_bugged_checker", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.py")
    interface.set_fatal_error()
    print(TestingUI.inst)
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("with_bugged_checker", __file__)