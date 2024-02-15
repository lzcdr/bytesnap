import os
from pathlib import Path
from bytesnap.generator_cpp import GeneratorCPP


#if __name__ == "__main__":
this_path = os.path.dirname(os.path.realpath(__file__))

gen = GeneratorCPP(
    project='example1',
    version='0.1.0',
    description='Bytesnap RPC example',
    author='',
    rpc_version='0.1.0'
)
gen.generate(
    Path(this_path) / "examples/example1/example1.txt", 
    Path(this_path) / "examples/example1", 
    "c:/Development/boost_1_84_0")

gen = GeneratorCPP(
    project='example2',
    version='0.1.0',
    description='Bytesnap RPC example',
    author='',
    rpc_version='0.1.0'
)
gen.generate(
    Path(this_path) / "examples/example2/example2.txt", 
    Path(this_path) / "examples/example2", 
    "c:/Development/boost_1_84_0")
