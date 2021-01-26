#!/usr/bin/env python
"""Quad Interpreter, by Segev Finer."""

from __future__ import print_function, division
import sys
import io
import re
import argparse


PY2 = sys.version_info[0] == 2

if PY2:
    input = raw_input


COMMENTS_RE = re.compile(r"/\*(?:.|\n)*?\*/|#.*")
OP_RE = re.compile(r"^[A-Z]+$")
ID_RE = re.compile(r"^[a-z_]+[a-z0-9_]*$")
INT_RE = re.compile(r"^[0-9]+$")
FLOAT_RE = re.compile(r"^[0-9]+\.[0-9]*$")


class QuadError(Exception):
    def __init__(self, lineno, msg):
        super(QuadError, self).__init__(lineno, msg)
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return "{}: {}".format(self.lineno, self.msg)


class QuadInst(object):
    def __init__(self, inst, lineno=None):
        self.inst = inst
        self.lineno = lineno
        tokens = inst.split()
        self.op, self.opers = tokens[0], tokens[1:]

        if not OP_RE.match(self.op):
            raise QuadError(lineno, "invalid op: '{}'".format(self.op))

        for i, oper in enumerate(self.opers):
            if ID_RE.match(oper):
                continue
            elif INT_RE.match(oper):
                self.opers[i] = int(oper)
            elif FLOAT_RE.match(oper):
                self.opers[i] = float(oper)
            else:
                raise QuadError(lineno, "invalid oper: '{}'".format(oper))

    def __repr__(self):
        return "QuadInst({!r}, {!r})".format(self.inst, self.lineno)

    def __str__(self):
        return self.inst


class QuadProgram(object):
    def __init__(self, src):
        self.code = []

        if isinstance(src, str):
            src = io.StringIO(src)

        for lineno, line in enumerate(src, 1):
            # Strip comments and leading/trailing whitespace
            line = COMMENTS_RE.sub("", line).strip()

            # Skip empty lines
            if not line:
                continue

            inst = QuadInst(line, lineno)
            self.code.append(inst)
            if inst.op == "HALT":
                break
        else:
            raise QuadError(lineno, "missing HALT")

    def __repr__(self):
        return "<QuadProgram: {} instructions>".format(len(self.code))


def is_type(value, type_):
    if PY2 and type_ is int:
        type_ = (int, long)

    return isinstance(value, type_)


class Namespace(object):
    class Entry(object):
        def __init__(self, lineno, value):
            self.lineno = lineno
            self.value = value

        def __repr__(self):
            return "Namespace.Entry({!r}, {!r})".format(self.lineno, self.value)

    def __init__(self):
        self._ns = {}

    def __repr__(self):
        return "Namespace({!r})".format(self._ns)

    def get(self, lineno, type_, name):
        return self._lookup(lineno, type_, name).value

    def set(self, lineno, type_, name, value):
        try:
            self._lookup(lineno, type_, name).value = value
        except KeyError:
            self._ns[name] = self.Entry(lineno, value)

    def _lookup(self, lineno, type_, name):
        if not isinstance(name, str):
            raise QuadError(lineno, "invalid identifier '{}'".format(name))

        entry = self._ns[name]

        if not is_type(entry.value, type_):
            raise QuadError(
                lineno,
                "type mismatch for variable '{}' (declared at line {}), "
                "expected {}, found {}".format(
                    name, entry.lineno, type_.__name__, type(entry.value).__name__))

        return entry


class QuadInterpreter(object):
    def __init__(self, prog, trace=False):
        self.prog = prog
        self.code = prog.code
        self.trace = trace
        self.pc = 1
        self.ns = Namespace()

    def run(self):
        while True:
            if self.pc is None:
                break

            inst = self.code[self.pc - 1]
            if self.trace:
                print("#{} {}".format(self.pc, inst), file=sys.stderr)
            self.pc += 1

            try:
                eval_inst = getattr(self, "eval_" + inst.op)
            except AttributeError:
                raise QuadError(inst.lineno, "unknown op: '{}'".format(inst.op))

            eval_inst(inst)

    def val(self, lineno, type_, oper):
        if isinstance(oper, str):
            return self.ns.get(lineno, type_, oper)
        else:
            if not is_type(oper, type_):
                raise QuadError(
                    lineno,
                    "type mismatch for operand, expected {}, found {}".format(
                        type_.__name__, type(oper).__name__))

            return oper

    def do_ASN(self, type_, inst):
        self.ns.set(inst.lineno, type_, inst.opers[0], self.val(inst.lineno, type_, inst.opers[1]))

    def do_PRT(self, type_, inst):
        print(self.val(inst.lineno, type_, inst.opers[0]))

    def do_INP(self, type_, inst):
        while True:
            try:
                value = type_(input("{} ({})? ".format(inst.opers[0], type_.__name__)))
                break
            except ValueError:
                print("Invalid input!")

        self.ns.set(inst.lineno, type_, inst.opers[0], value)

    def do_EQL(self, type_, inst):
        self.ns.set(
            inst.lineno, int, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) == self.val(inst.lineno, type_, inst.opers[2]))

    def do_NQL(self, type_, inst):
        self.ns.set(
            inst.lineno, int, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) != self.val(inst.lineno, type_, inst.opers[2]))

    def do_LSS(self, type_, inst):
        self.ns.set(
            inst.lineno, int, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) < self.val(inst.lineno, type_, inst.opers[2]))

    def do_GRT(self, type_, inst):
        self.ns.set(
            inst.lineno, int, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) > self.val(inst.lineno, type_, inst.opers[2]))

    def do_ADD(self, type_, inst):
        self.ns.set(
            inst.lineno, type_, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) + self.val(inst.lineno, type_, inst.opers[2]))

    def do_SUB(self, type_, inst):
        self.ns.set(
            inst.lineno, type_, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) - self.val(inst.lineno, type_, inst.opers[2]))

    def do_MLT(self, type_, inst):
        self.ns.set(
            inst.lineno, type_, inst.opers[0],
            self.val(inst.lineno, type_, inst.opers[1]) * self.val(inst.lineno, type_, inst.opers[2]))

    def do_DIV(self, type_, inst):
        if type_ is int:
            self.ns.set(
                inst.lineno, type_, inst.opers[0],
                self.val(inst.lineno, type_, inst.opers[1]) // self.val(inst.lineno, type_, inst.opers[2]))
        else:
            self.ns.set(
                inst.lineno, type_, inst.opers[0],
                self.val(inst.lineno, type_, inst.opers[1]) / self.val(inst.lineno, type_, inst.opers[2]))

    def eval_IASN(self, inst): self.do_ASN(int, inst)
    def eval_IPRT(self, inst): self.do_PRT(int, inst)
    def eval_IINP(self, inst): self.do_INP(int, inst)
    def eval_IEQL(self, inst): self.do_EQL(int, inst)
    def eval_INQL(self, inst): self.do_NQL(int, inst)
    def eval_ILSS(self, inst): self.do_LSS(int, inst)
    def eval_IGRT(self, inst): self.do_GRT(int, inst)
    def eval_IADD(self, inst): self.do_ADD(int, inst)
    def eval_ISUB(self, inst): self.do_SUB(int, inst)
    def eval_IMLT(self, inst): self.do_MLT(int, inst)
    def eval_IDIV(self, inst): self.do_DIV(int, inst)

    def eval_RASN(self, inst): self.do_ASN(float, inst)
    def eval_RPRT(self, inst): self.do_PRT(float, inst)
    def eval_RINP(self, inst): self.do_INP(float, inst)
    def eval_REQL(self, inst): self.do_EQL(float, inst)
    def eval_RNQL(self, inst): self.do_NQL(float, inst)
    def eval_RLSS(self, inst): self.do_LSS(float, inst)
    def eval_RGRT(self, inst): self.do_GRT(float, inst)
    def eval_RADD(self, inst): self.do_ADD(float, inst)
    def eval_RSUB(self, inst): self.do_SUB(float, inst)
    def eval_RMLT(self, inst): self.do_MLT(float, inst)
    def eval_RDIV(self, inst): self.do_DIV(float, inst)

    def eval_ITOR(self, inst):
        self.ns.set(
            inst.lineno, float, inst.opers[0],
            float(self.val(inst.lineno, int, inst.opers[1])))

    def eval_RTOI(self, inst):
        self.ns.set(
            inst.lineno, int, inst.opers[0],
            int(self.val(inst.lineno, float, inst.opers[1])))

    def eval_JUMP(self, inst):
        if not isinstance(inst.opers[0], int):
            raise QuadError(inst.lineno, "invalid instruction number: '{}'".format(inst.opers[0]))

        self.pc = inst.opers[0]

    def eval_JMPZ(self, inst):
        if not isinstance(inst.opers[0], int):
            raise QuadError(inst.lineno, "invalid instruction number: '{}'".format(inst.opers[0]))

        if self.ns.get(inst.lineno, int, inst.opers[1]) == 0:
            self.pc = inst.opers[0]

    def eval_HALT(self, inst):
        self.pc = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("-t", "--trace", action="store_true",
                        help="enable tracing")

    args = parser.parse_args()

    try:
        with open(args.source, "r") as f:
            program = QuadProgram(f)

        interpreter = QuadInterpreter(program, trace=args.trace)
        interpreter.run()
    except QuadError as e:
        print("{}:{}: error: {}".format(args.source, e.lineno, e.msg), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
