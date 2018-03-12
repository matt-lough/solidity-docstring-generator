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
    '''
    @summary: construct the module docstring
    '''
    docstring = "/**\n"
    docstring += " * Created on %s\n"
    docstring += " * @summary: \n"
    docstring += " * @author: %s\n"
    docstring += " */\n\n"
    docstring = docstring % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), getpass.getuser())
    return docstring


def construct_docstring(declaration, indent = 0):
    '''
    @summary: construct docstring according to the declaration
    @param declaration: the result of parse_declaration() reurns
    @param indent: the indent space number
    '''
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


def get_declaration(view, point):
    '''
    @summary: get the whole declaration of the class/def before the specified point
    @return: (True/False, region)
            True/False --- if the point in a declaration region
            region --- region of the declaration
    '''
    flag = False
    declaration_region = sublime.Region(0, 0)

    b_need_forward = False
    b_need_backward = False


    declaration = ""
    line = view.line(point)
    begin_point = line.begin()
    end_point = line.end()
    while True:
        if begin_point < 0:
            print("Can not find the start of the declaration")
            flag = False
            break
        line = view.line(begin_point)
        line_contents = view.substr(line)
        words = line_contents.split()
        print(words)
        if len(words) > 0:
            if words[0] in ("contract", "function"):
                flag = True
                begin_point = line.begin()
                end_point = line.end()
                break
        # get previous line
        begin_point = begin_point - 1
    if flag:
        # check from the line in where begin_point lives
        line = view.line(end_point)
        line_contents = view.substr(line).rstrip()
        while True:

            if end_point > view.size():
                print("Can not find the end of the declaration")
                flag = False
                break

            if (len(line_contents) >= 2) and (line_contents[-1] == "{"):
                print("reach the end of the declaration")
                flag = True
                end_point = line.begin() + len(line_contents) - 1
                break
            # get next line
            line = view.line(end_point + 1)
            end_point = line.end()
            line_contents = view.substr(line).rstrip()

    # check valid
    if end_point <= begin_point:
        flag = False

    if flag:
        declaration_region = sublime.Region(begin_point, end_point)

    return (flag, declaration_region)

def parse_declaration(declaration):
    '''
    @summary: parse the class/def declaration
    @param declaration: class/def declaration string
    @result:
        (typename, name, params)
        typename --- a string specify the type of the declaration, must be 'class' or 'def'
        name --- the name of the class/def
        params --- param list
    '''
    def rindex(l, x):
        index = -1
        if len(l) > 0:
            for i in range(len(l) - 1, -1, -1):
                if l[i] == x:
                    index = i
        return index

    def get_name(declaration, typename):
      print("get_name()")
      print("declaration ", declaration)
      print("typename ", typename)
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
        return False
      else:
        for types in SOLIDITY_DYNAMIC_TYPES:
          if re.match(types + '[0-9]{0,3}$', var) != None:
           return False
      return True

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
          print("found some cheeky returns")
          print(declaration)
          returns_raw, ignore = process_brackets(declaration)
          print(returns_raw)
          for return_name in returns_raw:
            # Returns can optionally define a type, we only want the name
            if not valid_variable(return_name):
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

    def run(self, edit):
        if not self.is_solidity_file():
          return
        for region in self.view.sel():
            if region.empty():
                line = self.view.line(region)
                previous_region = sublime.Region(0,line.begin())
                previous_contents = self.view.substr(previous_region)
                if len(previous_contents.strip()) == 0:
                    print("Start of the file. Inserting File Docstring")
                    self.view.insert(edit, 0, construct_file_docstring())
                else:
                    print("Not at the beginning of the file")

                tab_size = self.view.settings().get("tab_size", 4)
                print("tab_size = ", tab_size)
                flag, declaration_region = get_declaration(self.view, line.begin())
                print("declaration_region begin = %s, end = %s"%(declaration_region.begin(),
                    declaration_region.end()))
                declaration = self.view.substr(declaration_region)
                print("is_declaration: %s\ndeclaration: %s"%(flag, declaration))
                if flag:
                    result = parse_declaration(declaration)
                    indent = len(declaration) - len(declaration.lstrip())
                    docstring = construct_docstring(result, indent = int(indent))
                    print("docstring is: \n%s" %(docstring))
                    # Check that docstring doesn't already exist??? TODO
                    self.view.insert(edit, declaration_region.begin(), docstring)


