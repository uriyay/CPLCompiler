class Attrs:
    '''Synthesis attributes'''
    def __init__(self, value, val_type):
        self.value = value
        self.type = val_type

class Expr:
    def get_value(self):
        return self

class ID(Expr):
    def __init__(self, name, var_type):
        self.name = name
        self.type = var_type

    def get_value(self):
        return self.name

class Number(Expr):
    def __init__(self, value, val_type):
        self.value = value
        self.type = val_type

    def get_value(self):
        return self.value

class Temp(Expr):
    def __init__(self, name, var_type):
        self.name = name
        self.var_type = var_type

    def get_value(self):
        return self.name

class Label(Expr):
    def __init__(self, name):
        self.name = name

    def get_value(self):
        return self.name

class ADD(Expr):
    def __init__(self, a, b, is_sub=False):
        self.a = a
        self.b = b
        self.is_sub = is_sub

class MUL(Expr):
    def __init__(self, a, b, is_div=False):
        self.a = a
        self.b = b
        self.is_div = is_div

class NOT(Expr):
    def __init__(self, value):
        self.value = value

class OR(Expr):
    def __init__(self, a, b):
        self.a = a
        self.b = b

class AND(Expr):
    def __init__(self, a, b):
        self.a = a
        self.b = b

class RELOP(Expr):
    def __init__(self, a, b, relop):
        self.a = a
        self.b = b
        self.relop = relop