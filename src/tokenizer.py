#!/usr/bin/python3
import ply.lex as lex
import traceback
import sys
from re import escape

# lex part
RESERVED_WORDS = {
        'break': 'BREAK',
        'case': 'CASE',
        'default': 'DEFAULT',
        'else': 'ELSE',
        'float': 'FLOAT',
        'if': 'IF',
        'input': 'INPUT',
        'int': 'INT',
        'output': 'OUTPUT',
        'switch': 'SWITCH',
        'while': 'WHILE',
        'static_cast<int>': 'STATIC_CAST_INT',
        'static_cast<float>': 'STATIC_CAST_FLOAT'
}

tokens = (
    'BREAK',
    'CASE',
    'DEFAULT',
    'ELSE',
    'FLOAT',
    'IF',
    'INPUT',
    'INT',
    'OUTPUT',
    'SWITCH',
    'WHILE',

    'STATIC_CAST_INT',
    'STATIC_CAST_FLOAT',

    'INT_NUMBER',
    'FLOAT_NUMBER',
    'LETTER',
    'ID',
    'LPAREN', #(
    'RPAREN', #)
    'CLPAREN', #{
    'CRPAREN', #}
    'ALPAREN', #<
    'ARPAREN', #>
    'COMMA', #,
    'COLON', #:
    'SEMICOLON', #;
    'EQUAL', #=
    'NOT', #!
    'ADDOP',
    'MULOP',
    'OR', #||
    'AND', #&&
    'SPACE', #whitespace
    'RELOP',
    'COMMENT',

    'newline',
)

t_LPAREN = escape('(')
t_RPAREN = escape(')')
t_CLPAREN = '{'
t_CRPAREN = '}'
t_COMMA = ','
t_COLON = ':'
t_SEMICOLON = ';'
t_OR = escape('||')
t_AND = '&&'
t_SPACE = '[ \n]'
t_ADDOP = r'[\+-]'
t_MULOP = r'[\*/]'
t_COMMENT = '(?s)/\*(.*?)\*/'

t_ignore = '[\r ]'

has_tokenizing_error = False

def t_newline(t):
    r'\n'
    t.lexer.lineno += 1

def t_RELOP(t):
    '(==|!=|>=|<=|<|>|!|=)'
    if t.value == '!':
        t.type = 'NOT'
    elif t.value == '=':
        t.type = 'EQUAL'
    return t

def t_INT_NUMBER(t):
    '[0-9]+(\.[0-9]+)*'
    if '.' in t.value:
        t.type = 'FLOAT_NUMBER'
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

t_LETTER = '[a-zA-Z]'

def t_ID(t):
    '((static_cast<int>)|(static_cast<float>)|([a-zA-Z]([a-zA-Z0-9])*))'
    if t.value in RESERVED_WORDS:
        t.type = RESERVED_WORDS[t.value]
    return t

def t_error(t):
    global has_tokenizing_error
    has_tokenizing_error = True
    print("Illegal character '{}' in line {} char {}".format(t.value[0], t.lineno, t.lexpos), file=sys.stderr)
    t.lexer.skip(1)

lexer = lex.lex(debug=False)