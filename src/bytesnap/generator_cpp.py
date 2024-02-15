from datetime import datetime
import os
from pathlib import Path
import traceback
from jinja2 import Environment, FileSystemLoader
from bytesnap.logger import Logger, LoggerLevel

from bytesnap.parser import ASTProcessor, ServiceDescriptor, StructDescriptor


class GeneratorCPP:


    def __init__(self, project: str, version: str, description: str, author: str, rpc_version: str) -> None:
        self.sizeof_table = {
            'uint8_t': 1,
            'uint16_t': 2,
            'uint32_t': 4,
            'uint64_t': 8,
            'int8_t': 1,
            'int16_t': 2,
            'int32_t': 4,
            'int64_t': 8,
            'float': 4,
            'double': 8
        }

        self.project = project
        self.version = version
        self.description = description

        Logger.log(None, LoggerLevel.INFO, f'Loading templates')
        this_path = os.path.dirname(os.path.realpath(__file__))
        self.jinja_env = Environment(loader=FileSystemLoader(f"{this_path}/templates"))
        template = self.jinja_env.get_template("preamble.txt")
        self.preamble = template.render(
            project=project, version=version, description=description, author=author,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            rpc_version=rpc_version)
        Logger.log(None, LoggerLevel.INFO, f'Templates loaded ok')

    
    def cpp_sizeof(self, typename: str) -> int:
        return self.sizeof_table.get(typename, 0)


    def generate_header(self, output_folder: Path) -> None:
        Logger.log(None, LoggerLevel.INFO, f'Generating bytesnap.hpp')
        template = self.jinja_env.get_template("bytesnap.hpp.txt")
        content = template.render(preamble=self.preamble)
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(output_folder) / "bytesnap.hpp"
        file_path.write_text(content)
        Logger.log(None, LoggerLevel.INFO, f'bytesnap.hpp generated ok')


    def generate_cmake(self, ast_processor: ASTProcessor, 
                       project_name: str,
                       version_string: str, output_folder: Path,
                       boost_pathname: str) -> None:
        Logger.log(None, LoggerLevel.INFO, f'Generating CMakeLists.txt')
        methodnames = {}
        servicenames = []
        for servicename, service in ast_processor.services.items():
            servicenames.append(servicename)
            methodnames[servicename] = []
            for method in service.methods:
                methodname = method[0]    
                methodnames[servicename].append(methodname)

        template = self.jinja_env.get_template("CMakeLists.txt.txt")
        content = template.render(preamble=self.preamble,
                                  servicenames=servicenames, 
                                  methodnames=methodnames,
                                  version_string=version_string,
                                  boost_pathname=Path(boost_pathname).as_posix())
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(output_folder) / "CMakeLists.txt"
        file_path.write_text(content)
        Logger.log(None, LoggerLevel.INFO, f'CMakeLisits.txt generated ok')


    def generate_structs(self, ast_processor: ASTProcessor, output_folder: Path) -> None:
        Logger.log(None, LoggerLevel.INFO, f'Generating structures')
        #namespace = ast_processor.options.get("namespace", None)
        namespace = self.project
        for structname, struct in ast_processor.structs.items():
            self.generate_struct(output_folder, structname, struct, namespace)
        Logger.log(None, LoggerLevel.INFO, f'Structures generated ok')


    def generate_struct(self, output_folder: Path, structname: str, struct: StructDescriptor, namespace: str | None):
        # build include headers
        headers = ''
        for fieldname in struct.field_names:
            field = struct.fields[fieldname]
            if field.is_userdefined:
                headers += f'#include "{field.typename.lower()}.hpp"\n'

        # build fields
        init_list = []
        fields = ''
        for fieldname in struct.field_names:
            field = struct.fields[fieldname]
            typename = f'std::{field.typename}' if field.typename == 'string' else field.typename
            if field.is_vector:
                typename = f'std::vector<{typename}>'
            fieldtxt = f'    {typename} {fieldname}'
            if not field.assigned_value is None:
                if isinstance(field.assigned_value, list):
                    fieldtxt += f" = {{ {', '.join(str(v) for v in field.assigned_value)} }}"
                else:
                    fieldtxt += f" = {field.assigned_value}"
            elif not field.length_spec is None:
                # fieldtxt += f'({field.length_spec})'
                init_list.append(f'{fieldname}({field.length_spec})')
            fieldtxt += ";\n"
            fields += fieldtxt

        # build ctor
        init_list_txt = ''
        if init_list:
            init_list_txt = ' : ' + ', '.join(init_list)
        ctor = f'''    {structname}(){init_list_txt} {{}}
'''

        # build encode method
        encode_body = ''
        for fieldname in struct.field_names:
            field = struct.fields[fieldname]
            if field.is_vector:
                if field.typename == 'string':
                    template = self.jinja_env.get_template("vector_string_field_encode.txt")
                    encode_body += template.render(fieldname=fieldname)
                    encode_body += '\n'
                elif field.is_userdefined:
                    template = self.jinja_env.get_template("vector_userdef_field_encode.txt")
                    encode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                    encode_body += '\n'
                else:
                    sizeof = self.cpp_sizeof(field.typename)
                    if sizeof > 1:
                        template = self.jinja_env.get_template("vector_other_field_encode.txt")
                        encode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                        encode_body += '\n'
                    else:
                        template = self.jinja_env.get_template("vector_other_1_field_encode.txt")
                        encode_body += template.render(fieldname=fieldname)
                        encode_body += '\n'
            else:
                if field.typename == 'string':
                    template = self.jinja_env.get_template("scalar_string_field_encode.txt")
                    encode_body += template.render(fieldname=fieldname)
                    encode_body += '\n'
                elif field.is_userdefined:
                    template = self.jinja_env.get_template("scalar_userdef_field_encode.txt")
                    encode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                    encode_body += '\n'
                else:
                    template = self.jinja_env.get_template("scalar_other_field_encode.txt")
                    encode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                    encode_body += '\n'
        template = self.jinja_env.get_template("encode.txt")
        encode = template.render(structname=structname, encode_body=encode_body)
        encode += '\n'
        
        # build decode method
        decode_body = ''
        for fieldname in struct.field_names:
            field = struct.fields[fieldname]
            if field.is_vector:
                if field.typename == 'string':
                    template = self.jinja_env.get_template("vector_string_field_decode.txt")
                    decode_body += template.render(fieldname=fieldname)
                    decode_body += '\n'
                elif field.is_userdefined:
                    template = self.jinja_env.get_template("vector_userdef_field_decode.txt")
                    decode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                    decode_body += '\n'
                else:
                    sizeof = self.cpp_sizeof(field.typename)
                    if sizeof > 1:
                        template = self.jinja_env.get_template("vector_other_field_decode.txt")
                        decode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                        decode_body += '\n'
                    else:
                        template = self.jinja_env.get_template("vector_other_1_field_decode.txt")
                        decode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                        decode_body += '\n'
            else:
                if field.typename == 'string':
                    template = self.jinja_env.get_template("scalar_string_field_decode.txt")
                    decode_body += template.render(fieldname=fieldname)
                    decode_body += '\n'
                elif field.is_userdefined:
                    template = self.jinja_env.get_template("scalar_userdef_field_decode.txt")
                    decode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                    decode_body += '\n'
                else:
                    template = self.jinja_env.get_template("scalar_other_field_decode.txt")
                    decode_body += template.render(fieldname=fieldname, field_typename=field.typename)
                    decode_body += '\n'
        template = self.jinja_env.get_template("decode.txt")
        decode = template.render(structname=structname, decode_body=decode_body)
        decode += '\n'

        if namespace is None:
            namespace_begin = ''
            namespace_end = ''
        else:
            namespace_begin = f'namespace {namespace} {{'
            namespace_end = f'}} // namespace {namespace}'

        # build whole source
        template = self.jinja_env.get_template("hpp.txt")
        src = template.render(
            preamble=self.preamble,
            structname_lower=structname.lower(),
            datetime_string=datetime.now().strftime("%B %d, %Y %I:%M%p"),
            structname_upper=structname.upper(),
            headers=headers,
            namespace_begin=namespace_begin,
            structname=structname,
            fields=fields,
            ctor=ctor,
            encode=encode,
            decode=decode,
            namespace_end=namespace_end
        )
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(output_folder) / f'{structname.lower()}.hpp'
        file_path.write_text(src)


    def generate_services(self, ast_processor: ASTProcessor, output_folder: Path, max_msg_size: str) -> None:
        Logger.log(None, LoggerLevel.INFO, f'Generating services')
        #namespace = ast_processor.options.get("namespace", None)
        namespace = self.project
        for servicename, service in ast_processor.services.items():
            self.generate_service(output_folder, servicename, service, namespace, max_msg_size)
        Logger.log(None, LoggerLevel.INFO, f'Services generated ok')


    def generate_service(self, output_folder: Path, servicename: str, service: ServiceDescriptor, namespace: str | None, max_msg_size: str):
        template = self.jinja_env.get_template("method_id.hpp.txt")
        ids = service.get_list_of_method_ids()
        src = template.render(preamble=self.preamble, list_of_method_ids=ids, servicename=servicename, namespace=namespace)
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(output_folder) / f'{servicename.lower()}_method_id.hpp'
        file_path.write_text(src)
        
        names = [
            'service.hpp',
            'service.cpp',
            'client.hpp',
            'client.cpp',
            'client_test.cpp'
        ]
        client_includes = set()
        for method in service.methods:
            include1 = f'{method[1].lower()}'
            include2 = f'{method[2].lower()}'
            client_includes.add(include1)
            client_includes.add(include2)

        for name in names:
            template = self.jinja_env.get_template(f"{name}.txt")
            src = template.render(
                preamble=self.preamble,
                servicename=servicename, 
                methodnames=list(service.methodnames), 
                list_of_method_ids=ids, 
                methods=service.methods,
                client_includes=client_includes,
                namespace=namespace,
                max_msg_size=max_msg_size)
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            file_path = Path(output_folder) / f'{servicename.lower()}_{name}'
            file_path.write_text(src)

        for method in service.methods:
            methodname = method[0]
            request = method[1]
            response = method[2]
            for name in ['hpp', 'cpp']:
                template = self.jinja_env.get_template(f'service_method.{name}.txt')
                src = template.render(preamble=self.preamble, servicename=servicename.lower(), methodname=methodname.lower(), 
                                      request=request, response=response, namespace=namespace)
                Path(output_folder).mkdir(parents=True, exist_ok=True)
                file_path = Path(output_folder) / f'{servicename.lower()}_{methodname}.{name}'
                file_path.write_text(src)


    def generate_vst(self, output_folder: Path) -> None:
        Logger.log(None, LoggerLevel.INFO, f'Generating framework sources')
        vst_filenames = [
            'vst_client.hpp',
            'vst_buffer.hpp',
            'vst_connection.hpp',
            'vst_connection.hpp',
            'vst_io_context_pool.hpp',
            'vst_log_mockup.hpp',
            'vst_message.hpp',
            'vst_server.hpp'
        ]
        for name in vst_filenames:
            template = self.jinja_env.get_template(f"{name}.txt")
            src = template.render(preamble=self.preamble)
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            file_path = Path(output_folder) / name
            file_path.write_text(src)
        Logger.log(None, LoggerLevel.INFO, f'framework sources generated ok')

    
    def generate_readme1st(self, ast_processor: ASTProcessor, output_folder: Path) -> None:
        Logger.log(None, LoggerLevel.INFO, f'Generating readme.1st')
        template = self.jinja_env.get_template("readme.1st.txt")
    
        servicenames = set()
        structurenames = set()
        servicemethods = set()
    
        for structname, struct in ast_processor.structs.items():
            structurenames.add(structname) 

        for servicename, service in ast_processor.services.items():
            servicenames.add(servicename)
            for method in service.methods:
                servicemethods.add(f'{servicename.lower()}_{method[0].lower()}')
    
        src = template.render(
            project=self.project,
            version=self.version,
            servicenames=list(servicenames),
            structurenames=list(structurenames),
            servicemethods=list(servicemethods)
        )
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        file_path = Path(output_folder) / "readme.1st"
        file_path.write_text(src)
        Logger.log(None, LoggerLevel.INFO, f'readme.1st generated ok')


    def generate(self, sourceFile: Path, outputDir: Path, boost_pathname: str, max_msg_size: str) -> None:
        with sourceFile.open() as f:
            sourceCode = f.read()
        Logger.log(None, LoggerLevel.INFO, f'Parsing IDL file {sourceFile}')
        parser = ASTProcessor.build_parser()
        ast = parser.parse(sourceCode)
        astp = ASTProcessor()
        astp.process_ast(ast)
        Logger.log(None, LoggerLevel.INFO, f'IDL file {sourceFile} parsed ok.')
        self.generate_header(outputDir)
        self.generate_structs(astp, outputDir)
        self.generate_services(astp, outputDir, max_msg_size)
        self.generate_cmake(astp, self.project, self.version, outputDir, boost_pathname)
        self.generate_vst(outputDir)
        self.generate_readme1st(astp, outputDir)
        Logger.log(None, LoggerLevel.INFO, f'IDL file {sourceFile} processed ok.')
        Logger.log(None, LoggerLevel.INFO, f'C++ source files and CMake project descriptor genearated at {outputDir}')
    