import sys
from .expr import *

class Codegen:
    def __init__(self):
        self.code = []
        self.labels = []
        self.labels_mapping = {}
        self.temps = []
        self.temps_type = {}

    def get_code(self):
        return '\n'.join(['{}: {}'.format(l + 1, self.code[l]) for l in range(len(self.code))])

    def backpatching(self):
        for line_idx in range(len(self.code)):
            for label_name, label_lineno in self.labels_mapping.items():
                if label_name in self.code[line_idx]:
                    self.code[line_idx] = self.code[line_idx].replace(label_name, str(label_lineno))

    def add_insn(self, insn, *args):
        insn_text = '{} {}'.format(insn, ' '.join(str(arg.get_value()) for arg in args)) 
        self.code.append(insn_text)

    def get_insn_type(self, insn):
        insn_type = 'int' if insn[0] == 'I' else 'float'
        return insn_type
    
    def newlabel(self):
        label = 'l{}'.format(len(self.labels))
        self.labels.append(label)
        return label

    def label(self, label_name):
        #the next instruction will be labeled with label_name
        self.labels_mapping[label_name] = len(self.code) + 1

    def newtemp(self, var_type):
        temp_name = 't{}'.format(len(self.temps))
        temp = Temp(temp_name, var_type=var_type)
        self.temps.append(temp)
        self.temps_type[temp] = var_type
        return temp

    def check_args_types(self, insn, args_types):
        """
        Checks the arguments types of the instruction in order to see that there is no usage of the same variable to two different types
        @param insn: the instruction
        @param srgs_types: a mapping of arg's Attr to its type. If the matching arg type is None then the instruction type is taken
        """
        insn_type = self.get_insn_type(insn)
        for arg_idx,arg_info in enumerate(args_types.items()):
            arg,arg_type = arg_info
            if arg_type is None:
                arg_type = insn_type
            if arg.type != arg_type:
                print("error: got argument `{}` of type `{}` as the {}'nth argument to instruction {} (expected type `{}`".format(
                        arg, arg.type, arg_idx + 1, insn, arg_type
                    ),
                    file=sys.stderr)

    def ASN(self, a, b, is_float=False):
        'a := b'
        insn = 'IASN' if not is_float else 'RASN'
        self.check_args_types(insn, {a: None, b:None})
        self.add_insn(insn, a, b)

    def PRT(self, b, is_float=False):
        'print the value of b'
        insn = 'IPRT' if not is_float else 'RPRT'
        self.check_args_types(insn, {b: None})
        self.add_insn(insn, b)
    
    def INP(self, a, is_float=False):
        'read an integer to a'
        insn = 'IINP' if not is_float else 'RINP'
        self.check_args_types(insn, {a: None})
        self.add_insn(insn, a)

    def EQL(self, a, b, c, is_float=False):
        'if b=c then a=1 else a=0'
        insn = 'IEQL' if not is_float else 'REQL'
        self.check_args_types(insn, {a: 'int', b:None, c:None})
        self.add_insn(insn, a, b, c)

    def NQL(self, a, b, c, is_float=False):
        'if b!=c then a=1 else a=0'
        insn = 'INQL' if not is_float else 'RNQL'
        self.check_args_types(insn, {a: 'int', b:None, c:None})
        self.add_insn(insn, a, b, c)

    def LSS(self, a, b, c, is_float=False):
        'if b<c then a=1 else a=0'
        insn = 'ILSS' if not is_float else 'RLSS'
        self.check_args_types(insn, {a: 'int', b:None, c:None})
        self.add_insn(insn, a, b, c)

    def GRT(self, a, b, c, is_float=False):
        'if b>c then a=1 else a=0'
        insn = 'IGRT' if not is_float else 'RGRT'
        self.check_args_types(insn, {a: 'int', b:None, c:None})
        self.add_insn(insn, a, b, c)

    def ADD(self, a, b, c, is_float=False):
        'a := b + c'
        insn = 'IADD' if not is_float else 'RADD'
        self.check_args_types(insn, {a: None, b:None, c:None})
        self.add_insn(insn, a, b, c)

    def SUB(self, a, b, c, is_float=False):
        'a := b - c'
        insn = 'ISUB' if not is_float else 'RSUB'
        self.check_args_types(insn, {a: None, b:None, c:None})
        self.add_insn(insn, a, b, c)

    def MLT(self, a, b, c, is_float=False):
        'a := b * c'
        insn = 'IMLT' if not is_float else 'RMLT'
        self.check_args_types(insn, {a: None, b:None, c:None})
        self.add_insn(insn, a, b, c)

    def DIV(self, a, b, c, is_float=False):
        'a := b / c'
        insn = 'IDIV' if not is_float else 'RDIV'
        self.check_args_types(insn, {a: None, b:None, c:None})
        self.add_insn(insn, a, b, c)

    def CAST(self, a, b, is_float=False):
        'a := cast(b)'
        insn = 'RTOI' if not is_float else 'ITOR'
        cast_from_type = 'int' if insn[0] == 'I' else 'float'
        cast_to_type = 'int' if insn[-1] == 'I' else 'float'
        self.check_args_types(insn, {a: cast_to_type, b: cast_from_type})
        self.add_insn(insn, a, b)

    def JUMP(self, l):
        'jump to instruction number l'
        self.add_insn('JUMP', Label(l))

    def JMPZ(self, l, a):
        'if a=0 then jump to instruction number l else continue'
        insn = 'JMPZ'
        self.check_args_types(insn, {a: 'int'})
        self.add_insn(insn, Label(l), a)

    def HALT(self):
        'stop immediately'
        self.add_insn('HALT')