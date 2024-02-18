import os
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path
from bytesnap.generator_cpp import GeneratorCPP
from bytesnap.logger import Logger, LoggerLevel


DEFAULT_BOOST_PATH = '/usr/include/boost'

Logger(True, False).set_level(LoggerLevel.INFO)

boost_dir_pathname = input(
    f"Enter the boost path (leave blank for '{DEFAULT_BOOST_PATH}'): ")
if boost_dir_pathname == '':
    boost_dir_pathname = DEFAULT_BOOST_PATH

this_path = os.path.dirname(os.path.realpath(__file__))

tmp_dir_pathname = tempfile.mkdtemp()
print(f'Created temporary directory for test output: "{tmp_dir_pathname}"')

gen = GeneratorCPP(
    project='example',
    version='0.0.1',
    description='Bytesnap RPC test',
    author='',
    rpc_version='0.1.0'
)
gen.generate(
    Path(this_path) / "examples/example/example.txt",
    Path(tmp_dir_pathname),
    boost_dir_pathname,
    10000)

commands = [
    "mkdir build",
    "dir",
    "cd build && cmake ..",
    "cd build && cmake --build ."
] if sys.platform.startswith('win') else [
    "mkdir ./build",
    "ls -ls",
    "cd ./build && cmake ..",
    "cd ./build && cmake --build ."
]

for cmd in commands:
    print("Executing command:", cmd)
    try:
        output = subprocess.check_output(
            f'(cd {tmp_dir_pathname} && {cmd})',
            shell=True,
            stderr=subprocess.STDOUT,
            text=True)
        print("Output:")
        print(output)
    except subprocess.CalledProcessError as e:
        print(f"Error! Return code: {e.returncode}")

output_filenames = [
    'Debug/example_client.exe',
    'Debug/example_server.exe'
] if sys.platform.startswith('win') else [
    'example_client',
    'example_server'
]

we_are_good = True
for output_file in output_filenames:
    if not Path(f'{tmp_dir_pathname}/build/{output_file}').exists():
        print(f"Error! File '{tmp_dir_pathname}/build/{output_file}' does not exists")
        we_are_good = False

shutil.rmtree(tmp_dir_pathname)
print(f'Temporary directory for test output "{tmp_dir_pathname}" deleted ok')

if we_are_good:
    print("*****************************")
    print("Success! All tests passed OK.")
    print("*****************************")
