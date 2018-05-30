'''
Created on 2018-03-09
@summary: A solidity docstring plugin for sublime text 3.
@author: Matt Lough
@contact: im.mattlough@gmail.com
'''

'''
Docstrings are using Natspec
Reference: http://solidity.readthedocs.io/en/latest/layout-of-source-files.html?highlight=natspec
'''

import sublime
import sublime_plugin
import string
import datetime
import getpass
import os.path
import re

SOLIDITY_TYPES = [
  "address",
  "bool",
  "fixed",
  "string"
]

SOLIDITY_DYNAMIC_TYPES = [
  "bytes",
  "int",
  "uint"
]

def construct_file_docstring():
    """Generates the format for the file docstring"""
    docstring = "/**\n"
    docstring += " * Created on %s\n"
    docstring += " * @summary: \n"
    docstring += " * @author: %s\n"
    docstring += " */\n"
    docstring = docstring % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), getpass.getuser())
    return docstring


def construct_docstring(declaration, indent = 0):
    """Generates the format for the file docstring

    Keyword arguments:
    declaration -- Line of code, this should be the start of a function or contract
    indent -- The current indentation level where the docstring will be inserted
    """
    docstring = ""
    try:
        typename, name, params, returns = declaration
        lines = []
        lines.append("/**\n")
        # lines.append("\n")
        if typename == "contract":
            lines.append(" * @title: \n")
            pass
        elif typename == "function":
            lines.append(" * @dev: \n")

            if len(params):
                for param in params:
                    lines.append(" * @param {:s}\n".format(param))

            if len(returns):
              for return_var in returns:
                lines.append(" * @return {:s}\n".format(return_var))

        lines.append(" */\n")

        for line in lines:
            docstring += " " * indent + line

    except Exception as e:
        print(e)

    return docstring

def parse_declaration(declaration):
    def get_name(declaration, typename):
      name = ""
      index = declaration.find("(")
      if typename == "contract":
        name = declaration
      elif index > 0:
          name = declaration[:index]
          declaration = declaration[index:]
      else:
          name = "can not find the contract/function name"
      return name, declaration

    def get_declaration_type(declaration):
      typename = ""
      if declaration.startswith("contract"):
        typename = "contract"
        declaration = declaration[len("contract"):]
      elif declaration.startswith("function"):
        typename = "function"
        declaration = declaration[len("function"):]
      else:
        typename = "unsupported"
      return typename, declaration

    def valid_variable(var):
      if var in SOLIDITY_TYPES:
        return True
      else:
        for types in SOLIDITY_DYNAMIC_TYPES:
          if re.match(types + '[0-9]{0,3}$', var) != None:
           return True
      return False

    params = []
    returns = []

    declaration = declaration.strip()
    typename, declaration = get_declaration_type(declaration)
    name, declaration = get_name(declaration, typename)

    # process params string
    if typename != "contract":
      # extract params
      if (len(declaration) >= 2) and (declaration.find('(') != -1):
        params_raw, declaration = process_brackets(declaration)
        if len(params_raw) >= 2:
          for i in range(0, len(params_raw), 2):
            params.append(params_raw[i + 1])

        # Does this function return something?
        if declaration.find('returns') != -1:
          returns_raw, ignore = process_brackets(declaration)
          for return_name in returns_raw:
            # Returns can optionally define a type, we only want the name
            if valid_variable(return_name):
              continue
            returns.append(return_name)

    return(typename, name, params, returns)

def process_brackets(declaration):
      param_start = declaration.find('(') + 1
      param_end = declaration.find(')')
      if (param_end == -1):
        print("Multiple lines??")

      params_raw = declaration[param_start:param_end].split(' ')
      for i in range(0, len(params_raw)):
        params_raw[i] = params_raw[i].rstrip(',')
      return params_raw, declaration[param_end + 1:]

class DocstringCommand(sublime_plugin.TextCommand):
    def is_solidity_file(self):
        filename = self.view.file_name()
        _, ext = os.path.splitext(filename)
        if not ext == ".sol":
            sublime.error_message("This is not a Solidity file. Should end in .sol.")
            return False
        return True

    def process_file(self):
        line_pointer = 0
        while line_pointer <= self.view.size():
            line_region = self.view.line(line_pointer)
            line = self.view.substr(line_region).strip()
            if self.region_documented(line_region):
              print ("File already has a Docstring. Skipping..")
            elif line.startswith("pragma solidity"):
                self.insert_file_docstring(line_region)
            elif line.startswith("contract") or line.startswith("function"):
                self.insert_docstring(line_region)
            line_pointer = line_region.end() + 1

    def get_docstring(self, region):
      search_region = region
      # Try to avoid infinite loops..
      MAX_DOCSTRING_LINES = 20
      line_count = 1
      while line_count < MAX_DOCSTRING_LINES:
        search_region = self.view.line(search_region.begin() - 1)
        line = self.view.substr(search_region).strip()
        if line == "/**":
          # region.end() - 1 because we only want to include the docstring in the region
          return self.view.lines(sublime.Region(search_region.begin(), region.end() - 1))
        line_count += 1
      return ''

    def get_param_name(self, param_line):
      docstring_param = self.view.substr(param_line).strip().split(' ')
      return docstring_param[docstring_param.index('@param') + 1]

    def find_invalid_params(self):
      params = self.view.find_all('@param ', 0)
      invalid_regions = []
      for param in params:
        docstring_param_line = self.view.line(param)
        docstring_param = self.get_param_name(docstring_param_line)
        function_params, ignore = process_brackets(self.view.substr(self.find_closest_function(param)))
        if docstring_param not in function_params:
          invalid_regions.append(docstring_param_line)
      self.view.add_regions("invalid_params", invalid_regions, "invalid", "circle", sublime.DRAW_SQUIGGLY_UNDERLINE)

    def find_closest_function(self, region):
      function_region = self.view.find('function ', region.end())
      event_region = self.view.find('event ', region.end())
      if event_region.begin() == -1 or function_region.begin() < event_region.begin():
        return self.view.line(function_region)
      else:
        return self.view.line(event_region)

    def region_documented(self, region):
        if region.begin() == 0:
            return False
        previous_line = self.view.substr(self.view.line(region.begin()-1)).strip()
        # TODO: Make a better assumption that a docstring exists than looking for the end of a multi-line comment..
        # TODO: Find existing docstrings that might be out of date (complicated?)
        if previous_line == "*/":
            return True
        return False

    def get_indent(self, line):
      cleaned = line.lstrip(' ')
      return len(line) - len(cleaned)

    def insert_file_docstring(self, region):
        self.view.insert(self.edit, region.begin(), construct_file_docstring())

    def insert_docstring(self, region):
        line = self.view.substr(region)
        docstring = construct_docstring(parse_declaration(line), self.get_indent(line))
        self.view.insert(self.edit, region.begin(), docstring)

    def run(self, edit):
        if not self.is_solidity_file():
          return
        self.edit = edit
        self.process_file()
        self.find_invalid_params()

