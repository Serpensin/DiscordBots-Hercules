import os
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache


class Hercules:
    def __init__ (self, program_logger):
        self._program_logger = program_logger
        self._lua = self._getLuaInterpreter()
        if self._lua is None:
            self._program_logger.error("Could not find LUA 5.4")
            self._program_logger.info("Shutting down due to missing LUA 5.4")
            sys.exit(1)
        self._obfuscator_folder, self.obfuscator_file = self._detectObfuscator()
        if self._obfuscator_folder is None:
            self._program_logger.error("Could not find Obfuscator")
            self._program_logger.info("Shutting down due to missing Obfuscator")
            sys.exit(1)
        self.methods = [
            {'key': 'control_flow', 'name': 'Control Flow', 'bitkey': 0},
            {'key': 'variable_renaming', 'name': 'Variable Renaming', 'bitkey': 1},
            {'key': 'garbage_code', 'name': 'Garbage Code', 'bitkey': 2},
            {'key': 'opaque_predicates', 'name': 'Opaque Predicates', 'bitkey': 3},
            {'key': 'bytecode_encoding', 'name': 'Bytecode Encoding', 'bitkey': 4},
            {'key': 'string_encoding', 'name': 'String Encoding', 'bitkey': 5},
            {'key': 'compressor', 'name': 'Code Compressor', 'bitkey': 6},
        ]


    def isValidLUASyntax(self, lua_code: str, isFile: bool = False) -> tuple[bool,str]:
        if isFile:
            temp_file_path = lua_code
        else:
            with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, encoding='utf-8', mode='w') as temp_file:
                temp_file.write(lua_code)
                temp_file_path = temp_file.name

        result = subprocess.run(['luacheck', temp_file_path], capture_output=True, text=True)
        if result.returncode in [0,1]:
            return True, result.stdout
        else:
            if not isFile:
                os.remove(temp_file_path)
            return False, result.stdout

    def obfuscate(self, file_path: str, bitkey: int) -> tuple[bool,str]:
        old_wd = os.getcwd()
        os.chdir(self._obfuscator_folder)
        enabled_features = self._get_active_keys(bitkey)

        flags = " ".join([f"--{feature}" for feature in enabled_features])
        self._program_logger.info(f"Obfuscating file: {file_path} with flags: {flags}")
        
        try:
            result = subprocess.run([self._lua, "hercules.lua", file_path, flags, "--overwrite"],
                                    check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            
        except subprocess.CalledProcessError as e:
            self._program_logger.error(f"Error occurred: {e.output.decode()}\nFile: {file_path}")
            return False, e.output.decode()
        finally:
            os.chdir(old_wd)
        if result.returncode != 0:
            return False, result.stdout.decode()
        else:
            isValid, conout = self.isValidLUASyntax(file_path, True)
            if isValid:
                return True, conout
            else:
                self._program_logger.error(f"Obfuscation failed. Invalid LUA syntax in file: {file_path}")
                return False, conout

    @lru_cache(maxsize=None)
    def find_method(self, method_name):
        for method in self.methods:
            if method['name'] == method_name:
                return method
        return None

    @lru_cache(maxsize=None)
    def _get_active_keys(self, bitkey):
        max_bitkey = (1 << len(self.methods)) - 1
        if bitkey < 0 or bitkey > max_bitkey:
            raise ValueError(f"Invalid bitkey: {bitkey}. It must be between 0 and {max_bitkey}.")

        active_keys = []
        for method in self.methods:
            if bitkey & (1 << method['bitkey']):
                active_keys.append(method['key'])
        return active_keys

    def _getLuaInterpreter(self) -> str:
        LUA = shutil.which('lua54')
        if LUA is None:
            LUA = shutil.which('lua5.4')
            if LUA is None:
                LUA = shutil.which('lua')
                if LUA is None:
                    return None
                else:
                    result = subprocess.run([LUA, '-v'], capture_output=True, text=True)
                    if not '5.4' in result.stdout:
                        return None
                    else:
                        return "lua"
            else:
                return "lua5.4"
        else:
            return "lua54"

    def _detectObfuscator(self):
        folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Obfuscator', 'src')).replace('\\', '/')
        file = os.path.join(folder, 'hercules.lua').replace('\\', '/')
        if os.path.exists(os.path.join(folder, 'hercules.lua')):
            return folder, file
        return None

