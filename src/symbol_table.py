#!/usr/bin/python3
from . import error

class AlreadyExists(error.CompilerError):
    pass

class SymbolNotFound(error.CompilerError):
    pass

class Symbol:
    def __init__(self, name, sym_type):
        self.name = name
        self.sym_type = sym_type
        self.is_assigned = False

    def mark_assigned(self):
        """
        Mark this symbol as assigned with value.
        self.is_assigned helps to check that non-assigned symbols will not be assigned to other symbols
        """
        self.is_assigned = True

class SymbolTable:
    def __init__(self):
        table = {}
        self.tables = [table]

    def make_table(self):
        """
        Create a new symbol table for the current scope in the code
        """
        table = {}
        #push it to be first
        self.tables.insert(0, table)

    def pop_table(self):
        del self.tables[0]

    def insert(self, symbol):
        """
        Insert a symbol and symbol type to the current symbol table that belongs to this scope
        @raises AlreadyExists error
        """
        if symbol.name in self.tables:
            raise AlreadyExists('symbol `{}` already exists in the symbol table'.format(symbol))
        self.tables[0][symbol.name] = symbol

    def lookup(self, symbol_name):
        """
        Search for a symbol in all scopes, starting with the inner scope, moving outside to the containing scope and so on.
        @raises SymbolNotFound
        """
        for table in self.tables:
            if symbol_name in table:
                return table[symbol_name]
        raise SymbolNotFound('symbol `{}` not found in the symbol table'.format(symbol_name))
