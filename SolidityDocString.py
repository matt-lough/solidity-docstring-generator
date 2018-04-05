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
    docstring = "/**\n"
    docstring += " * Created on %s\n"
    docstring += " * @summary: \n"
    docstring += " * @author: %s\n"
    docstring += " */\n"
    docstring = docstring % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), getpass.getuser())
    return docstring


def construct_docstring(declaration, indent = 0):
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

    def process_brackets(declaration):
      param_start = declaration.find('(') + 1
      param_end = declaration.find(')')
      if (param_end == -1):
        print("Multiple lines??")

      params_raw = declaration[param_start:param_end].split(' ')
      for i in range(0, len(params_raw)):
        params_raw[i] = params_raw[i].rstrip(',')
      return params_raw, declaration[param_end + 1:]

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
        for i in range(0, len(params_raw), 2):
          # print("Parameter Type: {:s}".format(params_raw[i]))
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


class DocstringCommand(sublime_plugin.TextCommand):
    def is_solidity_file(self):
        filename = self.view.file_name()
        _, ext = os.path.splitext(filename)
        if not ext == ".sol":
            print("This is not a Solidity file. Should end in .sol.")
            return False
        return True


    def process_file(self):
        line_pointer = 0
        while line_pointer <= self.view.size():
            line_region = self.view.line(line_pointer)
            line = self.view.substr(line_region).strip()
            if line.startswith("pragma solidity"):
                self.insert_file_docstring(line_region)
            elif line.startswith("contract"):
                self.insert_docstring(line_region)
            elif line.startswith("function"):
                self.insert_docstring(line_region)
            line_pointer = line_region.end() + 1

    def region_documented(self, region):
        if region.begin() == 0:
            return False
        previous_line = self.view.substr(self.view.line(region.a-1)).strip()
        # TODO: Make a better assumption that a docstring exists than looking for the end of a multi-line comment..
        # TODO: Find existing docstrings that might be out of date (complicated?)
        if previous_line == "*/":
            return True
        return False

    def insert_file_docstring(self, region):
        if self.region_documented(region):
            print ("File already has a Docstring. Skipping..")
            return
        self.view.insert(self.edit, region.begin(), construct_file_docstring())

    def insert_docstring(self, region):
        if self.region_documented(region):
            print ("Docstring already exists. Skipping..")
            return
        line = self.view.substr(region)
        docstring = construct_docstring(parse_declaration(line))
        self.view.insert(self.edit, region.begin(), docstring)

    def insert_function_docstrings(self, edit):
        for function_region in self.function_regions:
            if self.region_documented(function_region):
                print ("Function already has a Docstring. Skipping..")
                continue
            line = self.view.substr(function_region)
            function_docstring = construct_docstring(parse_declaration(line))
            self.view.insert(edit, function_region.a, function_docstring)

    def run(self, edit):
        if not self.is_solidity_file():
          return
        self.edit = edit
        self.process_file()

