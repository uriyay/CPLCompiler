#!/usr/bin/python3
import ply.yacc as yacc
import traceback
import sys
from pprint import pprint

from error import CompilerError
from tokenizer import tokens, lexer

class SemanticError(CompilerError):
    pass

class SemanticState:
    def __init__(self):
        #inheritance attributes
        self.is_in_while = False

start = 'program'
debug = True

def log_debug(msg):
    if debug:
        print(msg)

def log_enter():
    call_stack = traceback.extract_stack()
    caller = call_stack[-2]
    print("In %s() (line %d)" % (caller.name, caller.lineno))

def p_error(p):
    stack_state_str = ' '.join([symbol.type for symbol in parser.symstack][1:])
    raise SemanticError('Syntax error in input! Parser State:{}, Stack:"{}", symbol:"{}", action: "{}"'.format(
        parser.state,
        stack_state_str,
        p,
        parser.action[parser.state]
    ))

def p_program(p):
    'program : declarations stmt_block'
    log_enter()
    p[0] = ('program', (p[1], p[2]))

def p_declarations_list(p):
    'declarations : declarations declaration'
    log_enter()
    decl_list = p[1][1]
    if p[2]:
        # if not a comment
        decl_list.append(p[2])
    p[0] = ('declarations', decl_list)

def p_declarations_term(p):
    'declarations : empty'
    log_enter()
    p[0] = ('declarations', [])

def p_declaration(p):
    'declaration : idlist COLON type SEMICOLON' 
    log_enter()
    p[0] = ('declaration', (p[1], p[3]), p.lineno(1))

def p_declaration_comment(p):
    'declaration : COMMENT'
    log_enter()

def p_type_int(p):
    'type : INT'
    log_enter()
    p[0] = ('type', 'int')

def p_type_float(p):
    'type : FLOAT'
    log_enter()
    p[0] = ('type', 'float')

def p_idlist_list(p):
    'idlist : idlist COMMA ID'
    log_enter()
    idlist1 = p[1][1]
    lineno = p[1][2]
    idlist1.append(p[3])
    p[0] = ('idlist', idlist1, lineno)

def p_idlist_term(p):
    'idlist : ID'
    log_enter()
    p[0] = ('idlist', [p[1]], p.lineno(1))

def p_stmt_block_list(p):
    'stmt_block : CLPAREN stmtlist CRPAREN' 
    log_enter()
    p[0] = ('stmt_block', p[2])

def p_stmt_block_empty(p):
    'stmt_block : empty'
    log_enter()
    p[0] = ('stmt_block', [])

def p_stmtlist_list(p):
    'stmtlist : stmtlist stmt'
    log_enter()
    stmtlist1 = p[1][1]
    stmtlist1.append(p[2])
    p[0] = ('stmtlist', stmtlist1)

def p_stmtlist_term(p):
    'stmtlist : empty'
    log_enter()
    p[0] = ('stmtlist', [])

def p_stmt_asg(p):
    'stmt : assignment_stmt'
    log_enter()
    p[0] = ('assignment_stmt', p[1], p.lineno(1))

def p_stmt_input(p):
    'stmt : input_stmt'
    log_enter()
    p[0] = ('input_stmt', p[1], p.lineno(1))

def p_stmt_output(p):
    'stmt : output_stmt'
    log_enter()
    p[0] = ('output_stmt', p[1], p.lineno(1))

def p_stmt_if(p):
    'stmt : if_stmt'
    log_enter()
    p[0] = ('if_stmt', p[1], p.lineno(1))

def p_stmt_while(p):
    'stmt : while_stmt'
    log_enter()
    p[0] = ('while_stmt', p[1], p.lineno(1))

def p_stmt_switch(p):
    'stmt : switch_stmt'
    log_enter()
    p[0] = ('switch_stmt', p[1], p.lineno(1))

def p_stmt_break(p):
    'stmt : break_stmt'
    log_enter()
    p[0] = ('break_stmt', p[1], p.lineno(1))

def p_stmt_block(p):
    'stmt : stmt_block'
    log_enter()
    p[0] = ('stmt_block', p[1], p.lineno(1))

def p_stmt_comment(p):
    'stmt : COMMENT'
    log_enter()
    p[0] = ('comment', p[1], p.lineno(1))

def p_assignment_stmt(p):
    'assignment_stmt : ID EQUAL expression SEMICOLON'
    log_enter()
    #ID, expression
    p[0] = (p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_input_stmt(p):
    'input_stmt : INPUT LPAREN ID RPAREN SEMICOLON'
    log_enter()
    p[0] = p[3]
    p.set_lineno(0, p.lineno(1))

def p_output_stmt(p):
    'output_stmt : OUTPUT LPAREN expression RPAREN SEMICOLON'
    log_enter()
    p[0] = p[3]
    p.set_lineno(0, p.lineno(1))

def p_if_stmt(p):
    'if_stmt : IF LPAREN boolexpr RPAREN stmt ELSE stmt'
    log_enter()
    p[0] = (p[3], p[5], p[7])
    p.set_lineno(0, p.lineno(1))

def p_while_stmt(p):
    'while_stmt : WHILE LPAREN boolexpr RPAREN stmt'
    log_enter()
    p[0] = (p[3], p[5])
    p.set_lineno(0, p.lineno(1))

def p_switch_stmt(p):
    'switch_stmt : SWITCH LPAREN expression RPAREN CLPAREN caselist DEFAULT COLON stmtlist CRPAREN'
    log_enter()
    #expression, caselist, stmtlist
    p[0] = (p[3], p[6], p[9])
    p.set_lineno(0, p.lineno(1))

def p_caselist_list(p):
    'caselist : caselist CASE INT_NUMBER COLON stmtlist'
    log_enter()
    caselist1 = p[1][1]
    #number, stmtlist
    case = (p[3], p[5])
    caselist1.append(case)
    p[0] = ('caselist', caselist1)

def p_caselist_term(p):
    'caselist : empty'
    log_enter()
    p[0] = ('caselist', [])

def p_break_stmt(p):
    'break_stmt : BREAK SEMICOLON'
    log_enter()
    p.set_lineno(0, p.lineno(1))

def p_boolexpr_or(p):
    'boolexpr : boolexpr OR boolterm'
    log_enter()
    p[0] = ('or', p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_boolexpr_term(p):
    'boolexpr : boolterm'
    log_enter()
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))

def p_boolterm_and(p):
    'boolterm : boolterm AND boolfactor'
    log_enter()
    p[0] = ('and', p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_boolterm_term(p):
    'boolterm : boolfactor'
    log_enter()
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))

def p_boolfactor_not(p):
    'boolfactor : NOT LPAREN boolexpr RPAREN'
    log_enter()
    p[0] = ('not', p[3])
    p.set_lineno(0, p.lineno(1))

def p_boolfactor_relop(p):
    'boolfactor : expression RELOP expression'
    log_enter()
    p[0] = ('relop', p[2], p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_expression_list(p):
    'expression : expression ADDOP term'
    log_enter()
    p[0] = ('addop', p[2], p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_expression_term(p):
    'expression : term'
    log_enter()
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))

def p_term_mulop(p):
    'term : term MULOP factor'
    log_enter()
    p[0] = ('mulop', p[2], p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_term_factor(p):
    'term : factor'
    log_enter()
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))

def p_factor_expr(p):
    'factor : LPAREN expression RPAREN'
    log_enter()
    p[0] = ('expression', p[2])
    p.set_lineno(0, p.lineno(2))

def p_factor_cast(p):
    'factor : CAST LPAREN expression RPAREN'
    log_enter()
    p[0] = ('cast', p[1], p[3])
    p.set_lineno(0, p.lineno(1))

def p_factor_id(p):
    'factor : ID'
    log_enter()
    p[0] = ('id', p[1])
    p.set_lineno(0, p.lineno(1))

def p_factor_num(p):
    'factor : number'
    log_enter()
    p[0] = ('number', p[1])
    p.set_lineno(0, p.lineno(1))

def p_CAST_int(p):
    'CAST : STATIC_CAST_INT'
    log_enter()
    p[0] = 'int'
    p.set_lineno(0, p.lineno(1))

def p_CAST_float(p):
    'CAST : STATIC_CAST_FLOAT'
    log_enter()
    p[0] = 'float'
    p.set_lineno(0, p.lineno(1))

def p_number_int(p):
    'number : INT_NUMBER'
    log_enter()
    p[0] = ('int', p[1])
    p.set_lineno(0, p.lineno(1))

def p_number_float(p):
    'number : FLOAT_NUMBER'
    log_enter()
    p[0] = ('float', p[1])
    p.set_lineno(0, p.lineno(1))

def p_empty(p):
    'empty :'
    log_enter()

parser = yacc.yacc()

def main(input_file):
    with open(input_file) as f:
        program = f.read()
    result = parser.parse(program, debug=True)
    pprint(result)

if __name__ == '__main__':
    main(*sys.argv[1:])
