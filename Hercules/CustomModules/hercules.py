import os
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from typing import Literal, Optional


class Hercules:
    """
    Hercules class provides functionalities to obfuscate LUA scripts using various methods.
    It also validates LUA syntax and manages the LUA interpreter and obfuscator detection.
    """

    def __init__(self, program_logger):
        """
        Initializes the Hercules class with a program logger.

        Args:
            program_logger: Logger object to log messages.
        """
        self._program_logger = program_logger
        self._lua = self._getLuaInterpreter()
        if not self._lua:
            self._log_and_exit("Could not find LUA 5.4", "Shutting down due to missing LUA 5.4")
        self._obfuscator_folder, self.obfuscator_file = self._detectObfuscator()
        if not self._obfuscator_folder:
            self._log_and_exit("Could not find Obfuscator", "Shutting down due to missing Obfuscator")
        self.methods = [
            {'key': 'control_flow', 'name': 'Control Flow', 'bitkey': 0, 'enabled': True},
            {'key': 'variable_renaming', 'name': 'Variable Renaming', 'bitkey': 1, 'enabled': True},
            {'key': 'garbage_code', 'name': 'Garbage Code', 'bitkey': 2, 'enabled': True},
            {'key': 'opaque_preds', 'name': 'Opaque Predicates', 'bitkey': 3, 'enabled': True},
            {'key': 'bytecode_encoder', 'name': 'Bytecode Encoding', 'bitkey': 4, 'enabled': False},
            {'key': 'string_encoding', 'name': 'String Encoding', 'bitkey': 5, 'enabled': True},
            {'key': 'compressor', 'name': 'Code Compressor', 'bitkey': 6, 'enabled': True},
            {'key': 'string_to_expr', 'name': 'String to Expression', 'bitkey': 7, 'enabled': False},
            {'key': 'virtual_machine', 'name': 'Virtual Machine', 'bitkey': 8, 'enabled': True},
            {'key': 'wrap_in_func', 'name': 'Function Wrapping', 'bitkey': 9, 'enabled': True},
            {'key': 'func_inlining', 'name': 'Function Inlining', 'bitkey': 10, 'enabled': False},
            {'key': 'dynamic_code', 'name': 'Dynamic Code', 'bitkey': 11, 'enabled': False},
        ]

    def _log_and_exit(self, error_msg, info_msg):
        """
        Logs an error message and exits the program.

        Args:
            error_msg: Error message to log.
            info_msg: Informational message to log before exiting.
        """
        self._program_logger.error(error_msg)
        self._program_logger.info(info_msg)
        sys.exit(1)

    def isValidLUASyntax(self, lua_code: str, isFile: bool = False) -> tuple[bool, str]:
        """
        Validates the syntax of the given LUA code.

        Args:
            lua_code: LUA code as a string or file path.
            isFile: Boolean indicating if lua_code is a file path.

        Returns:
            A tuple containing a boolean indicating if the syntax is valid and the output message.
        """
        if not isFile:
            with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, encoding='utf-8', mode='w') as temp_file:
                temp_file.write(lua_code)
                temp_file_path = temp_file.name
        else:
            temp_file_path = lua_code

        result = subprocess.run(['luacheck', temp_file_path], capture_output=True, text=True)
        if result.returncode in [0, 1]:
            return True, result.stdout
        else:
            if not isFile:
                os.remove(temp_file_path)
            return False, result.stdout

    def obfuscate(self, file_path: str, bitkey: int, optional_preset: Optional[Literal["min", "mid", "max"]]) -> tuple[bool, str]:
        """
        Obfuscates the given LUA file using the specified bitkey and optional preset.

        Args:
            file_path: Path to the LUA file to be obfuscated.
            bitkey: Bitkey representing the obfuscation methods to use.
            optional_preset: Optional preset for obfuscation level ("min", "mid", "max").

        Returns:
            A tuple containing a boolean indicating if the obfuscation was successful and the output message.
        """
        old_wd = os.getcwd()
        os.chdir(self._obfuscator_folder)
        enabled_features = self._get_active_keys(bitkey)

        flags = [f"--{feature}" for feature in enabled_features]
        if optional_preset:
            flags.append(f"--{optional_preset}")
        self._program_logger.info(f"Obfuscating file: {file_path} with flags: {flags}")

        try:
            result = subprocess.run([self._lua, "hercules.lua", file_path] + flags + ["--overwrite"],
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
        """
        Finds a method by its name.

        Args:
            method_name: Name of the method to find.

        Returns:
            The method dictionary if found, otherwise None.
        """
        return next((method for method in self.methods if method['name'] == method_name), None)

    @lru_cache(maxsize=None)
    def _get_active_keys(self, bitkey):
        """
        Gets the active keys based on the given bitkey.

        Args:
            bitkey: Bitkey representing the obfuscation methods to use.

        Returns:
            A list of active method keys.
        """
        max_bitkey = (1 << len(self.methods)) - 1
        if bitkey < 0 or bitkey > max_bitkey:
            raise ValueError(f"Invalid bitkey: {bitkey}. It must be between 0 and {max_bitkey}.")

        return [method['key'] for method in self.methods if bitkey & (1 << method['bitkey'])]

    def _getLuaInterpreter(self) -> str:
        """
        Detects the LUA interpreter.

        Returns:
            The name of the LUA interpreter if found, otherwise None.
        """
        for lua_version in ['lua54', 'lua5.4', 'lua']:
            LUA = shutil.which(lua_version)
            if LUA:
                if lua_version == 'lua':
                    result = subprocess.run([LUA, '-v'], capture_output=True, text=True)
                    if '5.4' not in result.stdout:
                        continue
                return lua_version
        return None

    def _detectObfuscator(self):
        """
        Detects the obfuscator folder and file.

        Returns:
            A tuple containing the obfuscator folder and file path if found, otherwise (None, None).
        """
        folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Obfuscator', 'src')).replace('\\', '/')
        file = os.path.join(folder, 'hercules.lua').replace('\\', '/')
        return (folder, file) if os.path.exists(file) else (None, None)
