# Bytesnap RPC Framework

Bytesnap RPC is a lightweight RPC (Remote Procedure Call) framework based on C++ Boost.Asio, designed to simplify communication between distributed systems. It utilizes Python to generate C++ source code from a custom Interface Definition Language (IDL) file, making it easier to define and implement remote interfaces.

## Features

- **Lightweight**: Designed for easy prototyping, ensuring minimal overhead for communication between distributed components.

- **Custom IDL**: Remote interfaces are defined using a custom IDL file, allowing for clear and concise specification of remote procedure calls and data structures.

- **Code Generation**: Python scripts are utilized to automatically generate C++ source code from the custom IDL file, streamlining the implementation of remote interfaces.

- **Based on Boost.Asio**: Leveraging the power of Boost.Asio for asynchronous I/O and networking operations, providing a robust foundation for network communication.

- **Binary Protocol**: Utilizes a binary protocol for efficient data transmission, minimizing overhead and maximizing performance in network communication.

- **Built-in Serializer**: Includes a built-in serializer for seamless serialization and deserialization of data, simplifying the handling of complex data structures.


## Getting Started

To get started with Bytesnap RPC, follow these steps:

1. **Prerequisites**: Ensure that you have installed on your system:

- *C++ 20 Compiler*
- *C++ Boost library version 1.84 or higher*
- *Python version 3.10 or higher*
- *CMake version 3.15 or higher*

2. **Install**: To install Bytesnap RPC framework, follow these steps.

    2.1. *Clone the Repository*
    ```console
    git clone https://github.com/lzcdr/bytesnap.git
    ```
    2.2. *Create a Virtual Environment*
    ```console
    python3 -m venv .venv
    ```
    2.3. *Activate the Virtual Environment*
    - for Linux
    ```console
    source .venv/bin/activate
    ```
    - for Windows
    ```console
    # in cmd.exe
    .venv\Scripts\activate.bat
    # in PowerShell
    .venv\Scripts\activate.ps1
    ```
    2.4. *Install Requirements* 
    ```console
    pip install -r requirements.txt
    ```

3. **Define Interfaces**: Create a custom IDL file to define the remote interfaces and data structures for your application, see examples below.

4. **Generate Code**: Use the provided Python script to generate C++ source code from the custom IDL file.
    ```console
    # for Linux
    bytesnap_run.sh
    # for Windows
    bytesnap_run.bat
    ```

    Then answer some questions:
    ```console
    [?] Project name: example
    [?] Version string: 0.0.1
    [?] Description: ...
    [?] Author: ...
    [?] Source IDL file: src/examples/example/example.txt
    [?] Output dir: ../build/example
    [?] Boost dir: c:/boost_1_84_0
    [?] Maximum size of the message in bytes: 65535
    ```

5. **Integrate with Your Project**: Incorporate the generated C++ source code into your C++ project and start using Bytesnap RPC to facilitate remote communication. See *'readme.1st'* in the output folder for instructions.

## Example

Here's a simple example of defining a remote interface using the custom IDL file:

```python
const SIGNATURE = { 0xDEAD, 0xBEEF }
const CODE_LENGTH = 2
const ATTACHMENT = { "this is example", "(c) 2024" }

struct Header {
    signature: vector<uint64_t> = SIGNATURE
    code: vector<uint8_t>(CODE_LENGTH)
    attachment: vector<string> = ATTACHMENT
}

struct UserInfo {
    login: string
    num_messages: uint32_t
}

struct UserQueryRequest {
    header: Header
    user_logins: vector<string>
}

struct UserQueryResponse {
    header: Header
    user_infos: vector<UserInfo>
}

service Example {
    user_query: UserQueryRequest -> UserQueryResponse
}
```

After generating the code, you will get a set of project files in the chosen output directory.
To use them, you must define request processors on the server side (*'example_user_query.cpp'*) and test requests on the client side (*'example_client_test.cpp'*).

In *'example_user_query.cpp'* replace
```c
    // TODO - process request, build response
    UserQueryResponse response;
```
with
```c
    UserQueryResponse response;
    response.user_infos.resize(request.user_logins.size());
    std::size_t i = 0;
    for (std::string& login : request.user_logins) {
        UserInfo& info = response.user_infos[i];
        info.login = login;
        info.num_messages = i;
        i++;
    }
```

In *'example_client_test.cpp'* replace
```c
    example::UserQueryRequest request;
    example::UserQueryResponse reply;

    for (int i = 0; i < 100; i++)
        assert(client.example_user_query_request(request, reply) == true);
```
with
```c
    example2::UserQueryRequest request;
    example2::UserQuesryResponse reply;

    request.user_logins.push_back("alpha");
    request.user_logins.push_back("beta");
    request.user_logins.push_back("gamma");

    for (int i = 0; i < 100; i++) {
        assert(client.example_user_query_request(request, reply) == true);
        assert(reply.user_infos.size() == 3);

        assert(reply.user_infos[0].login == "alpha");
        assert(reply.user_infos[0].num_messages == 0);

        assert(reply.user_infos[1].login == "beta");
        assert(reply.user_infos[1].num_messages == 1);

        assert(reply.user_infos[2].login == "gamma");
        assert(reply.user_infos[2].num_messages == 2);
    }
```

## IDL description

### Basic Concepts

In Bytesnap RPC IDL you define structures, services and constants. Python-style comment lines are supported.

The structure basically follows the simple C-like structure, that is, it is a composition of named variables (structure fields) of supported data types. 

Example:
```python
struct SomeStrcuture {
    # example of field with scalar datatype int32_t
    integerField: int32_t

    # example of initialized field with scalar datatype
    # float
    floatField: float = 3.1415926

    # example of initialized field with vector datatype
    vectorField: vector<string> = { "hello", "world" }

    # example of field with scalar user-defined datatype
    # scalar user-defined datatypes can not be 
    # initialzied
    structField: SomeOtherStructure

    # example of field with vector user-defined datatype
    # vector user-defined datatypes can not be 
    # initialized
    vectorStructField: vector<SomeOtherStructure>

    # example of field with fixed-length vector datatype
    fixedLengthVectorField: vector<float>(16)

    # fixed-length vectors can be initialized as well
    anotherFixedLengthVectorField: vector<int8_t>(4) = { 1, 2, 3, 4 }
}
```

Supported datatypes include scalar types, user-defined types (structures) and vector types.

Scalar types are:
-   *uint8_t*
-   *uint16_t*
-   *uint32_t*
-   *uint64_t*
-   *int8_t*
-   *int16_t*
-   *int32_t*
-   *int64_t*
-   *float*
-   *double*
-   *string (corresponds to std::string)*

Vector datatypes correspond to std::vector. If structure fields of vector datatypes are neither initialized with some values nor have a predetermined fixed length, then they will be created empty by default.

Structure fields (of scalar and vector of scalar types) may be initialized with constants. Examples of const definitions:
```python
const SIGNATURE = { 0x0A, 0x0B, 0x0C, 0x0D }
const PI = 3.1415926
const MAX = 100
const WORDS = { "hello", "world" }
```

The service is composed of named methods (procedures) that define the request and response structures used for RPC communication. The client sends the request structure and receives the response, while the server does the opposite, i.e., it receives and processes the request and sends back the response. Example of service definition:
```python
service SomeService {
    method1: SomeRequestStruct -> SomeResponseStruct
    method2: SomeOtherRequestStruct -> SomeOtherResponseStruct
}
```


### IDL grammar specification

This is a semi-formal definition of grammar in terms of the Lark parsing toolkit for Python (https://github.com/lark-parser/lark)
```
start: definition+
definition: const | struct | service
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
```
