import traceback
import sys
from pprint import pprint

from error import CompilerError
from tokenizer import tokens, lexer
import lexical_parser
from symbol_table import SymbolTable, AlreadyExists, Symbol
from codegen import Codegen
from expr import *

class UnexpectedSymbol(CompilerError):
    pass

class TypeMismatch(CompilerError):
    pass

class UsedBeforeAssignedError(CompilerError):
    pass

class Compiler:
    def __init__(self, program):
        self.code_text = program
        self.ast = None
        self.symbol_table = SymbolTable()
        self.codegen = Codegen()
        self.cur_lineno = 1
        self.has_errors = False

        #a stack of exit labels, this attribute will be used for BREAK stmt in order to know where to jump to
        self.while_exit_label = []

    def assert_symbol(self, symbol, symbol_name):
        if symbol != symbol_name:
            raise UnexpectedSymbol('exptected symbol `{}`, got: `{}`'.format(symbol_name, symbol))

    def assert_symbol_one_of(self, symbol, *symbols_names):
        if symbol not in symbols_names:
            raise UnexpectedSymbol('exptected symbol to be one of `{}`, got: `{}`'.format(symbols_names, symbol))

    def type_max(self, *types):
        if 'float' in types:
            return 'float'
        return 'int'

    def run(self):
        self.ast = lexical_parser.parser.parse(self.code_text, debug=False)
        if lexical_parser.tokenizer.has_tokenizing_error or lexical_parser.has_lexical_error:
            self.has_errors = True
        self.create_temp_vars()
        self.handle_program(self.ast)
        if not self.has_errors:
            #replace labels names with labels numbers
            self.codegen.backpatching()
            return '\n'.join(self.codegen.code)
        return None

    def create_temp_vars(self):
        self.temp_vars = {
            'int': self.codegen.newtemp('int'),
            'float': self.codegen.newtemp('float')
        }

    def handle_program(self, program_ast):
        self.assert_symbol(program_ast[0], 'program')
        self.handle_declarations(program_ast[1][0])
        self.handle_stmt_block(program_ast[1][1])
        self.codegen.HALT()

    def handle_declarations(self, declarations_ast):
        self.assert_symbol(declarations_ast[0], 'declarations')
        for decl in declarations_ast[1]:
            self.handle_declaration(decl)

    def handle_declaration(self, declaration_ast):
        self.assert_symbol(declaration_ast[0], 'declaration')
        self.cur_lineno = declaration_ast[2]
        idlist = self.handle_idlist(declaration_ast[1][0])
        var_type = self.handle_type(declaration_ast[1][1])
        for var_id in idlist:
            self.symbol_table.insert(Symbol(var_id, var_type))

    def handle_idlist(self, idlist_ast):
        self.assert_symbol(idlist_ast[0], 'idlist')
        #no need to verify variable names, since this step was done in the tokenizer
        return idlist_ast[1]

    def handle_type(self, type_ast):
        self.assert_symbol(type_ast[0], 'type')
        self.assert_symbol_one_of(type_ast[1], 'float', 'int')
        return type_ast[1]

    def handle_stmt_block(self, stmt_block_ast):
        self.assert_symbol(stmt_block_ast[0], 'stmt_block')
        self.symbol_table.make_table()
        if stmt_block_ast[1]:
            self.handle_stmtlist(stmt_block_ast[1])
        self.symbol_table.pop_table()

    def handle_stmtlist(self, stmtlist_ast):
        self.assert_symbol(stmtlist_ast[0], 'stmtlist')
        for stmt in stmtlist_ast[1]:
            self.handle_stmt(stmt)

    def handle_stmt(self, stmt_ast):
        self.assert_symbol_one_of(
            stmt_ast[0],
            'assignment_stmt',
            'input_stmt',
            'output_stmt',
            'if_stmt',
            'while_stmt',
            'switch_stmt',
            'break_stmt',
            'stmt_block',
            'comment'
        )
        handle_func = getattr(self, 'handle_{}'.format(stmt_ast[0]))
        self.cur_lineno = stmt_ast[2]
        try:
            handle_func(stmt_ast[1])
        except CompilerError as err:
            print('error in line {}: {}'.format(self.cur_lineno, repr(err)), file=sys.stderr)
            self.has_errors = True

    def handle_comment(self, comment_ast):
        pass

    def handle_assignment_stmt(self, assignment_stmt_ast):
        var_id = assignment_stmt_ast[0]
        var_sym = self.symbol_table.lookup(var_id)
        var_type = var_sym.sym_type
        expr = self.handle_expression(assignment_stmt_ast[1])
        expr_value = self.get_value_from_attr(expr)

        if expr.type != var_type:
            if var_type == 'int':
                raise TypeMismatch('Cannot assign `{}` to variable `{}` of type `{}`'.format(expr.type, var_id, var_type))
            elif var_type == 'float':
                expr_value = self.cast(expr_value, var_type)
        #assign
        self.codegen.ASN(ID(var_id, var_type), expr_value, is_float=(var_type=='float'))
        #mark this var as assigned
        var_sym.mark_assigned()

    def handle_expression(self, expression_ast):
        if expression_ast[0] == 'addop':
            attrs = self.handle_expression_addop(expression_ast)
        else:
            attrs = self.handle_term(expression_ast)
        return attrs

    def handle_expression_addop(self, addop_expr_ast):
        self.assert_symbol_one_of(addop_expr_ast[1], '+', '-')
        addop = addop_expr_ast[1]
        term = self.handle_term(addop_expr_ast[3])
        term_value = self.get_value_from_attr(term, alloc_temp=True)
        expr = self.handle_expression(addop_expr_ast[2])
        expr_value = self.get_value_from_attr(expr, alloc_temp=False)

        val_type = self.type_max(expr.type, term.type)

        #cast if needed
        if expr.type != term.type:
            if term.type != val_type:
                term_value = self.cast(term_value, dest_type=val_type, alloc_temp=True)
            elif expr.type != 'float':
                expr_value = self.cast(expr_value, dest_type=val_type, alloc_temp=False)

        val = ADD(expr.value, term.value, is_sub=(addop == '-'))
        if addop == '+':
            self.codegen.ADD(self.temp_vars[val_type], expr_value, term_value, is_float=val_type == 'float')
        elif addop == '-':
            self.codegen.SUB(self.temp_vars[val_type], expr_value, term_value, is_float=val_type == 'float')
        return Attrs(val, val_type)

    def handle_term(self, term_ast):
        if term_ast[0] == 'mulop':
            attrs = self.handle_term_mulop(term_ast)
        else:
            attrs = self.handle_factor(term_ast)
        return attrs

    def get_value_from_attr(self, attr, alloc_temp=False):
        """
        Gets the value of an Attr
        if alloc_temp is True - a temp var is created if attr is not Number, ID or Temp
        """
        res_value = attr.value
        if type(attr.value) not in (Number, ID, Temp):
            res_value = self.temp_vars[attr.type]
            if alloc_temp:
                tmp = self.codegen.newtemp(attr.type)
                self.codegen.ASN(tmp, res_value, is_float=attr.type == 'float')
                res_value = tmp
        return res_value

    def cast(self, value, dest_type, alloc_temp=False):
        """
        value can be a value of Number, ID or Temp
        """
        dest = None
        if alloc_temp:
            if type(value) is not Temp:
                #if value is not a Temp we need to allocate a new temp
                dest = self.codegen.newtemp(value.type)
            else:
                #if value is a Temp - use the 
                dest = value
        else:
            dest = self.temp_vars[dest_type]
        self.codegen.CAST(dest, value, is_float=dest_type == 'float')
        return dest

    def handle_term_mulop(self, term_ast):
        mulop = term_ast[1]
        self.assert_symbol_one_of(mulop, '*', '/')
        factor = self.handle_factor(term_ast[3])
        factor_value = self.get_value_from_attr(factor, alloc_temp=True)
        term = self.handle_term(term_ast[2])
        term_value = self.get_value_from_attr(term)

        val_type = self.type_max(term.type, factor.type)

        #cast if needed
        if term.type != factor.type:
            if factor.type != val_type:
                factor_value = self.cast(factor_value, dest_type=val_type, alloc_temp=True)
            elif term.type != val_type:
                term_value = self.cast(term_value, dest_type=val_type, alloc_temp=False)

        val = MUL(term.value, factor.value, is_div=(mulop == '/'))
        if mulop == '/':
            self.codegen.DIV(self.temp_vars[val_type], term_value, factor_value, is_float=val_type == 'float')
        elif mulop == '*':
            self.codegen.MLT(self.temp_vars[val_type], term_value, factor_value, is_float=val_type == 'float')
        return Attrs(val, val_type)

    def handle_factor(self, factor_ast):
        """Returns factor type"""
        self.assert_symbol_one_of(factor_ast[0],
                'expression', 'cast', 'id', 'number', 'temp')
        attrs = None
        if factor_ast[0] == 'expression':
            attrs = self.handle_expression(factor_ast[1])
        elif factor_ast[0] == 'cast':
            attrs = self.handle_cast(factor_ast)
        elif factor_ast[0] == 'id':
            var_id = factor_ast[1]
            var_sym = self.symbol_table.lookup(var_id)
            if not var_sym.is_assigned:
                raise UsedBeforeAssignedError('symbol `{}` is used before assigned a value'.format(var_id))
            var_type = var_sym.sym_type
            attrs = Attrs(ID(var_id, var_type), var_type)
        elif factor_ast[0] == 'number':
            val_type, val = factor_ast[1]
            attrs = Attrs(Number(val, val_type), val_type)
        elif factor_ast[0] == 'temp':
            #handle temp variables - inner use
            temp = factor_ast[1]
            temp_type = factor_ast[2]
            attrs = Attrs(temp, temp_type)
        return attrs

    def handle_cast(self, cast_ast):
        self.assert_symbol_one_of(cast_ast[1], 'int', 'float')
        cast_type = cast_ast[1]
        expr = self.handle_expression(cast_ast[2])
        if cast_type != expr.type:
            #add code of RTOI or ITOR
            self.codegen.CAST(
                self.temp_vars[cast_type],
                self.temp_vars[expr.type],
                cast_type == 'float'
            )
        #change the type
        expr.type = cast_type
        return expr

    def handle_input_stmt(self, input_stmt_ast):
        var_id = input_stmt_ast
        var_sym = self.symbol_table.lookup(var_id)
        var_type = var_sym.sym_type
        #gen code for input for int/float
        self.codegen.INP(ID(var_id, var_type), is_float=var_type == 'float')
        var_sym.mark_assigned()
        return Attrs(var_id, var_type)

    def handle_output_stmt(self, output_stmt_ast):
        expr = self.handle_expression(output_stmt_ast)
        expr_value = self.get_value_from_attr(expr)
        self.codegen.PRT(expr_value, is_float=expr.type == 'float')        

    def handle_if_stmt(self, if_stmt_ast):
        l_after = self.codegen.newlabel()
        l_else = self.codegen.newlabel()
        self.handle_boolexpr(if_stmt_ast[0])
        #jump to l_else if boolexpr == 0
        #the Then part
        self.codegen.JMPZ(l_else, self.temp_vars['int'])
        self.handle_stmt(if_stmt_ast[1])
        self.codegen.JUMP(l_after)
        #the Else part
        self.codegen.label(l_else)
        self.handle_stmt(if_stmt_ast[2])
        #after the if - both Then and Else parts goes here
        self.codegen.label(l_after)

    def handle_while_stmt(self, while_stmt_ast):
        l_boolexpr = self.codegen.newlabel()
        l_exit = self.codegen.newlabel()
        #handle the while boolexpr
        self.codegen.label(l_boolexpr)
        self.handle_boolexpr(while_stmt_ast[0])
        #jump to l_exit if boolexpr == 0
        self.codegen.JMPZ(l_exit, self.temp_vars['int'])
        #mark the while as in-the-middle for BREAK statement purposes
        self.while_exit_label.append(l_exit)
        #handle the while body
        self.handle_stmt(while_stmt_ast[1])
        #delete while's l_exit label for the stack
        self.while_exit_label.pop()
        self.codegen.JUMP(l_boolexpr)
        self.codegen.label(l_exit)

    def handle_switch_stmt(self, switch_stmt_ast):
        tmp = self.codegen.newtemp('int')
        expr = self.handle_expression(switch_stmt_ast[0])
        expr_value = self.get_value_from_attr(expr)
        if expr.type != 'int':
            raise TypeMismatch('Expected switch expression to be of type `int`, got type `{}` instead'.format(expr.type))
        self.codegen.ASN(tmp, expr_value, is_float=False)
        #create if-else for the switch cases
        caselist = switch_stmt_ast[1]
        self.assert_symbol(caselist[0], 'caselist')
        start_if_ast = None
        last_if_ast = None
        #TODO: for some reason the else-part label is not generated well..
        for case_num, case_stmtlist in caselist[1]:
            boolexpr = ('relop', '==', ('temp', tmp, 'int'), ('number', ('int', case_num)))
            then_stmt = ('stmt_block', ('stmt_block', case_stmtlist))
            else_stmt = None
            if_ast = ('if_stmt', [boolexpr, then_stmt])
            if start_if_ast is None:
                #the start if_ast to parse eventually
                start_if_ast = if_ast
            if last_if_ast:
                #append if_ast as else part of the last if ast
                last_if_ast[1].append(if_ast)
            #mark this if_ast as the last_if_ast
            last_if_ast = if_ast
        #now add the default part as else part to the last_if_ast
        last_if_ast[1].append(('stmt_block', ('stmt_block', switch_stmt_ast[2])))
        #handle the huge if stmt
        self.handle_stmt(start_if_ast)

    def handle_break_stmt(self, break_stmt_ast):
        if not self.while_exit_label:
            raise UnexpectedSymbol('got `break` statement outside a while loop')
        self.codegen.JUMP(self.while_exit_label[-1])

    def handle_boolexpr(self, boolexpr_ast):
        expr = None
        if boolexpr_ast[0] == 'or':
            boolexpr = self.handle_boolexpr(boolexpr_ast[1])
            tmp = self.codegen.newtemp('int')
            self.codegen.ASN(tmp, self.temp_vars['int'], is_float=False)
            boolterm = self.handle_boolterm(boolexpr_ast[2])
            #the result of boolterm is stored in self.temp_vars['int']
            expr = OR(boolexpr, boolterm)
            #OR is equivalent to A + B >= 1, i.e A + B > 0
            self.codegen.ADD(self.temp_vars['int'], tmp, self.temp_vars['int'], is_float=False)
            self.codegen.GRT(self.temp_vars['int'], self.temp_vars['int'], Number(0, 'int'), is_float=False)
        else:
            boolterm = self.handle_boolterm(boolexpr_ast)
            expr = boolterm
        return expr

    def handle_boolterm(self, boolterm_ast):
        expr = None
        if boolterm_ast[0] == 'and':
            boolterm = self.handle_boolterm(boolterm_ast[1])
            tmp = self.codegen.newtemp('int')
            self.codegen.ASN(tmp, self.temp_vars['int'], is_float=False)
            boolfactor = self.handle_boolfactor(boolterm_ast[2])
            #the result of boolfactor is stored in self.temp_vars['int']
            expr = AND(boolterm, boolfactor)
            #AND is equivalent to A + B == 2
            self.codegen.ADD(self.temp_vars['int'], tmp, self.temp_vars['int'], is_float=False)
            self.codegen.EQL(self.temp_vars['int'], self.temp_vars['int'], Number(2, 'int'), is_float=False)
        else:
            boolfactor = self.handle_boolfactor(boolterm_ast)
            expr = boolfactor
        return expr

    def handle_boolfactor(self, boolfactor_ast):
        self.assert_symbol_one_of(boolfactor_ast[0], 'not', 'relop')
        expr = None
        if boolfactor_ast[0] == 'not':
            boolexpr = self.handle_boolexpr(boolfactor_ast[1])
            expr = NOT(boolexpr)
            #if A = 0 then A = 1 else A = 0
            self.codegen.EQL(self.temp_vars['int'], self.temp_vars['int'], Number(0, 'int'), is_float=False)
        elif boolfactor_ast[0] == 'relop':
            relop = boolfactor_ast[1]
            if relop == '>=':
                #translate >= to not less than
                boolfactor_ast = list(boolfactor_ast)
                boolfactor_ast[1] = '<'
                boolfactor_ast = tuple(boolfactor_ast)
                not_ast = ('not', boolfactor_ast)
                expr = self.handle_boolfactor(not_ast)
            if relop == '<=':
                #translate <= to not bigger than
                boolfactor_ast = list(boolfactor_ast)
                boolfactor_ast[1] = '>'
                boolfactor_ast = tuple(boolfactor_ast)
                not_ast = ('not', boolfactor_ast)
                expr = self.handle_boolfactor(not_ast)
            else:
                expression1 = self.handle_expression(boolfactor_ast[2])
                expression1_value = self.get_value_from_attr(expression1, alloc_temp=True)
                expression2 = self.handle_expression(boolfactor_ast[3])
                expression2_value = self.get_value_from_attr(expression2)
                
                expr_type = self.type_max(expression1.type, expression2.type)

                if expression1.type != expression2.type:
                    if expression1.type != expr_type:
                        expression1_value = self.cast(expression1_value, expr_type, alloc_temp=True)
                    elif expression2.type != expr_type:
                        expression2_value = self.cast(expression2_value, expr_type)
                expr = RELOP(expression1, expression2, relop)
                if relop == '==':
                    self.codegen.EQL(self.temp_vars['int'], expression1_value, expression2_value, is_float=(expr_type == 'float'))
                elif relop == '!=':
                    self.codegen.NQL(self.temp_vars['int'], expression1_value, expression2_value, is_float=(expr_type == 'float'))
                elif relop == '>':
                    self.codegen.GRT(self.temp_vars['int'], expression1_value, expression2_value, is_float=(expr_type == 'float'))
                elif relop == '<':
                    self.codegen.LSS(self.temp_vars['int'], expression1_value, expression2_value, is_float=(expr_type == 'float'))
        return expr


def main(input_file):
    with open(input_file) as f:
        program = f.read()
    compiler = Compiler(program)
    quad_code = compiler.run()
    if quad_code:
        print('Quad code:')
        print(compiler.codegen.get_code())
        with open('out.quad', 'w') as fp:
            fp.write(quad_code)

if __name__ == '__main__':
    main(sys.argv[1])
