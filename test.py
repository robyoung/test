from collections import namedtuple
import subprocess
import textwrap
import os
from pprint import pprint

import requests
from lazyme.string import color_print


TESTS = """
pass dev-merge   master-rebase dev-merge    master-rebase
pass dev-merge   master-merge
pass dev-merge   master-rebase
pass dev-rebase  master-merge
pass dev-rebase  master-rebase
pass dev-merge   master-merge  dev-rebase   master-merge
pass dev-rebase  master-merge  dev-merge    master-merge
pass dev-merge   dev-merge     master-merge
pass dev-rebase  dev-merge     master-merge
pass dev-merge   dev-rebase    master-merge
pass dev-merge   dev-rebase    dev-merge    master-merge
"""


GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_BASE = 'https://api.github.com/repos/robyoung/test'


def sh(command, *args):
    return subprocess.check_output(command.format(*args), shell=True, stderr=subprocess.STDOUT)


def yellow(string):
    color_print(string, color='yellow', bold=True)


class MergeFailure(Exception):
    pass


BaseStep = namedtuple('BaseStep', 'branch method')


class Step(BaseStep):

    def _update_readme_line(self, branch_name, line):
        if branch_name in line:
            return line.replace('unchanged', 'changed')
        return line

    def _update_readme(self, branch_name):
        with open('README.md', 'r+') as f:
            lines = f.readlines()
            f.seek(0)
            f.writelines([
                self._update_readme_line(branch_name, line)
                for line in lines
            ])

    def create_feature(self, branch_name):
        yellow(">>>   Create feature {}".format(branch_name))
        sh('git checkout dev')
        sh('git checkout -b {}', branch_name)
        self._update_readme(branch_name)
        sh('touch {}', branch_name)
        sh('git add *')
        sh('git commit -m {}', branch_name)
        sh('git push origin HEAD')

    def merge(self, branch_name):
        yellow(
            ">>>   Merge {} into {} with {}".format(
                branch_name, self.branch, self.method))
        self.merge_pr(self.create_pr(branch_name))

    def create_pr(self, branch_name):
        pr_title = '{} -> {} ({})'.format(
            branch_name, self.branch, self.method)
        url = GITHUB_BASE + '/pulls'
        resp = requests.post(
            url,
            json=dict(
                title=pr_title,
                body=None,
                head=branch_name,
                base=self.branch),
            headers={
                'Authorization': 'token {}'.format(GITHUB_TOKEN),
            }
        )
        if resp.status_code != 201:
            print("FAIL creating PR")
            print(resp.status_code)
            pprint(resp.json())
            raise ValueError()
        return resp.json()['number']

    def merge_pr(self, pr_number):
        url = GITHUB_BASE + '/pulls/{}/merge'.format(pr_number)
        resp = requests.put(
            url,
            json=dict(merge_method=self.method),
            headers={
                'Authorization': 'token {}'.format(GITHUB_TOKEN),
            }
        )
        result = "pass" if resp.status_code == 200 else "fail"
        if result == "fail":
            print("FAIL merging PR")
            print(resp.status_code)
            pprint(resp.json())

            raise MergeFailure


    def __str__(self):
        return "{}-{}".format(self.branch, self.method)


BaseTest = namedtuple('BaseTest', 'n expect steps')


class Test(BaseTest):
    def branch_name(self, step_n):
        return 'feature-{}-{}'.format(self.n, step_n)


    def setup_readme(self):
        sh("git checkout dev")
        with open('README.md', 'a') as f:
            for step in range(1, 10):
                f.writelines([
                    '*{}* unchanged\n'.format(self.branch_name(step)),
                    '\n'
                ])
        sh("git add README.md")
        sh("git cm -m 'setup readme'")
        sh("git push -f origin HEAD")
        sh("git branch -D master")
        sh("git checkout -b master")
        sh("git push -f origin HEAD")
        sh("git checkout dev")


    def reset(self):
        yellow("> reset")
        sh("git checkout begining")
        for branch in ['dev', 'master']:
            sh("git branch -D {}".format(branch))
            sh("git checkout -b {}".format(branch))
            sh("git push -f origin HEAD")
        sh("git checkout dev")

    def __str__(self):
        return "{} expecting {} steps: {}".format(
            self.n, self.expect, ", ".join(map(str, self.steps)))


def parse_tests(tests):
    def parse_step(step):
        return Step(*step.split('-'))

    def parse_test(n, test):
        parts = test.split()
        expect = parts[0]
        steps = parts[1:]
        return Test(n, expect, [parse_step(s) for s in steps])

    return [
        parse_test(n, test)
        for n, test in enumerate(TESTS.strip().splitlines(), 1)
    ]


def run_test(test):
    if test.n > 1:
        print("")
    yellow("> Running Test {}".format(test))
    test.setup_readme()
    feature_n = 0
    try:
        for step in test.steps:
            yellow(">>  Running Step {}".format(step))
            if step.branch == 'dev':
                feature_n += 1
                branch_name = test.branch_name(feature_n)
                step.create_feature(branch_name)
            else:
                branch_name = 'dev'
            step.merge(branch_name)
    except MergeFailure:
        if test.expect == "pass":
            raise AssertionError("Expected pass got fail")
    else:
        if test.expect == "fail":
            raise AssertionError("Expected fail got pass")
    yellow("> SUCCESS!!")
    test.reset()


def main():
    tests = parse_tests(TESTS)
    for test in tests:
        run_test(test)


if __name__ == '__main__':
    main()
