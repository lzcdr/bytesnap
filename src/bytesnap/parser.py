from lark import Lark, ParseTree

from bytesnap.logger import Logger, LoggerLevel


class TypeDescriptor:


    def __init__(self, typename: str, is_vector: bool, is_userdefined: bool, length_spec: int | None, assigned_value: int | float | str | list | None) -> None:
        self.typename = typename
        self.is_vector = is_vector
        self.is_userdefined = is_userdefined
        self.length_spec = length_spec
        self.assigned_value = assigned_value
    

    def __str__(self) -> str:
        return f'TypeDescriptor: typename={self.typename}, is_vector={self.is_vector}, is_userdefined={self.is_userdefined}, length_spec={self.length_spec}, assigned_value={self.assigned_value}'


class StructDescriptor:


    def __init__(self) -> None:
        self.field_names = list()
        self.fields = dict()


    def __str__(self) -> str:
        output_string = ''.join(f"\n\t{key} => {value}" for key, value in self.fields.items())
        return f'StructDescriptor: fields:{output_string}'
    

    def append_field(self, fieldname: str, typedescriptor: TypeDescriptor) -> bool:
        if fieldname in self.fields:
            return False
        self.field_names.append(fieldname)
        self.fields[fieldname] = typedescriptor
        return True


class ServiceDescriptor:


    def __init__(self) -> None:
        self.methodnames = set()
        self.methods = list()
    

    def __str__(self) -> str:
        output_string = ''.join(f"\n\t{v[0]} : {v[1]} -> {v[2]}" for v in self.methods)
        return f'ServiceDescriptor: methods:{output_string}'
    

    def append_method(self, methodname: str, requestname: str, responsename: str) -> bool:
        if methodname in self.methodnames:
            return False
        self.methodnames.add(methodname)
        self.methods.append((methodname, requestname, responsename))
        return True
    

    def get_list_of_method_ids(self) -> list[tuple[int, str]]:
        return list(enumerate(self.methodnames))


class ASTProcessor:


    def __init__(self) -> None:
        self.constants = dict()
        self.structs = dict()
        self.services = dict()
        self.options = dict()
        self.standard_typenames = {
            'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
            'int8_t', 'int16_t', 'int32_t', 'int64_t',
            'float', 'double', 'string'
        }

    
    def get_node_location(self, node: ParseTree) -> tuple[int, int]:
        if hasattr(node, 'meta'):
            return (node.meta.line, node.meta.column)
        else:
            return None


    def process_ast(self, ast: ParseTree) -> bool:
        for child in ast.children:
            if not self.process_constant(child):
                return False
        for child in ast.children:
            if not self.process_struct(child):
                return False
        for structname, struct in self.structs.items():
            if not self.validate_struct(structname, struct):
                return False
        for child in ast.children:
            if not self.process_service(child):
                return False
        for servicename, service in self.services.items():
            if not self.validate_service(servicename, service):
                return False
        for child in ast.children:
            if not self.process_options(child):
                return False
        return True


    def process_options(self, node: ParseTree) -> bool:
        if node.children[0].data == "options":
            for option in node.children[0].children:
                name = option.children[0].value.replace('"', '')
                value = option.children[1].value.replace('"', '')
                self.options[name] = value
        return True
    

    def process_constant(self, node: ParseTree) -> bool:
        if node.children[0].data == "const":
            name = node.children[0].children[0]
            if name in self.constants:
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'constant {name} redefinition')
                return False
            value = self.process_value(node.children[0].children[1])
            self.constants[name] = value
        return True
    

    def process_service(self, node: ParseTree) -> bool:
        if node.children[0].data == "service":
            name = node.children[0].children[0]
            if name in self.services:
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'service {name} redefinition')
                return False
            if name in self.structs:
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'structure with same name {name} defined')
                return False
            if name in self.constants:
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'constant with same name {name} defined')
                return False
            servciedescriptor = ServiceDescriptor()
            for method in node.children[0].children[1:]:
                methodname = method.children[0].value
                requestname = method.children[1].value
                responsename = method.children[2].value
                if not servciedescriptor.append_method(methodname=methodname, requestname=requestname, responsename=responsename):
                    Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'method with name {method} already defined')
                    return False
            self.services[name] = servciedescriptor
        return True
    

    def validate_service(self, servicename: str, service: ServiceDescriptor) -> bool:
        for method in service.methods:
            name = method[0]
            request = method[1]
            response = method[2]
            if not request in self.structs:
                Logger.log(None, LoggerLevel.ERROR, f'error processing service {servicename}, method {name}: undefined request struct type {request}')
                return False
            if not response in self.structs:
                Logger.log(None, LoggerLevel.ERROR, f'error processing service {servicename}, method {name}: undefined response struct type {response}')
                return False
        return True
    

    def process_struct(self, node: ParseTree) -> bool:
        if node.children[0].data == "struct":
            name = node.children[0].children[0]
            if name in self.structs:
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'structure {name} redefinition')
                return False
            if name in self.constants:
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'constant with same name {name} defined')
                return False
            structdescriptor = StructDescriptor()
            for field in node.children[0].children[1:]:
                field_name = field.children[0].value
                typename_node = field.children[1]
                assignment_node = field.children[2] if len(field.children) == 3 else None
                typedescriptor = self.process_typedescriptor(typename_node, assignment_node)
                if typedescriptor is None:
                    return False
                if not structdescriptor.append_field(fieldname=field_name, typedescriptor=typedescriptor):
                    Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'field with name {field_name} already defined')
                    return False
            self.structs[name] = structdescriptor
        return True
    

    def validate_struct(self, structname: str, struct: StructDescriptor) -> bool:
        for fieldname, field in struct.fields.items():
            if not field.typename in self.standard_typenames:
                if not field.typename in self.structs:
                    Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: undefined typename {field.typename}')
                    return False
                field.is_userdefined = True
            else:
                field.is_userdefined = False
            if not field.length_spec is None:
                if not isinstance(field.length_spec, int):
                    Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: non-integer vector length specifier {field.length_spec}')
                    return False
                if field.length_spec <= 0:
                    Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: non-positive vector length specifier {field.length_spec}')
                    return False
            if not field.assigned_value is None:
                if field.is_vector:
                    if not isinstance(field.assigned_value, list):
                        Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                        return False
                    if len(field.assigned_value) < 1:
                        Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: can not assign empty list')
                        return False
                    if self.is_integer_typename(field.typename):
                        if not isinstance(field.assigned_value[0], int):
                            Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                            return False
                    elif self.is_float_typename(field.typename):
                        if not isinstance(field.assigned_value[0], float):
                            Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                            return False
                    elif field.typename == "string":
                        if not isinstance(field.assigned_value[0], str):
                            Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                            return False
                    else:
                        Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: assignment for user defined types is not supported')
                        return False
                else:
                    if self.is_integer_typename(field.typename):
                        if not isinstance(field.assigned_value, int):
                            Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                            return False
                    elif self.is_float_typename(field.typename):
                        if not isinstance(field.assigned_value, float):
                            Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                            return False
                    elif field.typename == "string":
                        if not isinstance(field.assigned_value[0], str):
                            Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: incompatible type of assigned value {field.assigned_value}')
                            return False
                    else:
                        Logger.log(None, LoggerLevel.ERROR, f'error processing struct {structname}, field {fieldname}: assignment for user defined types is not supported')
                        return False
        return True
    

    def is_integer_typename(self, typename: str) -> bool:
        if typename in self.standard_typenames:
            if typename == "float" or typename == "double" or typename == "string":
                return False
            return True
        return False
    

    def is_float_typename(self, typename: str) -> bool:
        if typename == "float" or typename == "double":
            return True
        return False


    def process_typedescriptor(self, typename_node: ParseTree, assignment_node: ParseTree) -> TypeDescriptor | None:
        if assignment_node is None:
            assigned_value = None
        else:
            if assignment_node.children[0].data == "const_name":
                assigned_value_name = str(assignment_node.children[0].children[0].value)
                assigned_value = self.constants.get(assigned_value_name, None)
                if assigned_value is None:
                    Logger.log(self.get_node_location(assignment_node), LoggerLevel.ERROR, f'error in assignment specifier: undefined constant {assigned_value_name}')
                    return None
            else:
                assigned_value = self.process_value(assignment_node.children[0])

        if typename_node.children[0].data == "simple_typename":
            typename = typename_node.children[0].children[0].value
            return TypeDescriptor(typename, is_vector=False, is_userdefined=False, length_spec=None, assigned_value=assigned_value)
        else:
            typename = typename_node.children[0].children[0].value
            if len(typename_node.children[0].children) == 2:
                length_spec_node = typename_node.children[0].children[1]
                if length_spec_node.children[0].type == 'NAME':
                    length_spec_const = str(length_spec_node.children[0].value)
                    length_spec = self.constants.get(length_spec_const, None)
                    if length_spec is None:
                        Logger.log(self.get_node_location(typename_node), LoggerLevel.ERROR, f'error in vector length specifier: undefined constant {length_spec_const}')
                        return None
                elif length_spec_node.children[0].type == 'INT':
                    length_spec = int(length_spec_node.children[0].value)
                else:
                    Logger.log(self.get_node_location(typename_node), LoggerLevel.ERROR, f'unsupported vector size specifier type')
                    return None
                return TypeDescriptor(typename, is_vector=True, is_userdefined=False, length_spec=length_spec, assigned_value=assigned_value)
            else:
                return TypeDescriptor(typename, is_vector=True, is_userdefined=False, length_spec=None, assigned_value=assigned_value)


    def process_value(self, node: ParseTree) -> int | float | str | list | None:
        if node.children[0].data == "vector_value":
            res = list()
            for child in node.children[0].children:
                value = self.process_scalar_value(child)
                res.append(value)
            if not all(isinstance(e, type(res[0])) for e in res):
                Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'can not mix different value types in the vector')
                return None
            return res
        else:
            return self.process_scalar_value(node.children[0])


    def process_scalar_value(self, node: ParseTree) -> int | float | str | None:
        if node.data == "int_value":
            value = node.children[0].value
            return int(value)
        elif node.data == "hex_int_value":
            value = node.children[0].value
            return int(value, 16)
        elif node.data == "bin_int_value":
            value = node.children[0].value
            return int(value, 2)
        elif node.data == "float_value":
            value = node.children[0].value
            return float(value)
        elif node.data == "string_value":
            value = node.children[0].value
            return str(value)
        else:
            Logger.log(self.get_node_location(node), LoggerLevel.ERROR, f'unsupported value type {node.data}')
            return None


    @staticmethod
    def build_parser():
        grammar = '''
start: definition+

definition: const | struct | service | options

options: "options" "{" option+ "}"

option: NAME "=" STRING

const: "const" NAME "=" value

value: scalar_value | vector_value

scalar_value: INT -> int_value
    | HEX_INT -> hex_int_value
    | BIN_INT -> bin_int_value
    | FLOAT -> float_value
    | STRING -> string_value

vector_value: "{" scalar_value ("," scalar_value)* "}"

struct: "struct" NAME "{" struct_field+ "}"

struct_field: NAME ":" typename (assignment)?

typename: simple_typename | vector_typename

simple_typename: NAME

vector_typename: "vector" "<" NAME ">" (length_spec)?

length_spec: "(" (INT | NAME) ")"

assignment: "=" (value | const_name)

const_name: NAME

service: "service" NAME "{" service_method+ "}"

service_method: NAME ":" NAME "->" NAME

HEX_INT: "0x" /[0-9A-Fa-f]+/
BIN_INT: "0b" /[01]+/

%import common.CNAME -> NAME
%import common.INT
%import common.FLOAT
%import common.ESCAPED_STRING -> STRING
%import common.WS
%ignore WS

COMMENT: "#" /[^\\n]*/ _NEWLINE
_NEWLINE: "\\n"
%ignore COMMENT
'''
        return Lark(grammar, start='start', propagate_positions=True)
