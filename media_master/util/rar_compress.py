import subprocess
import os
import sys
from ..error import DirNotFoundError
from .check import check_file_environ_path

import logging

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def rar_compress(
    input_path_set: set,
    output_dir: str,
    output_filename: str,
    compress_level=5,
    solid_compress_bool=False,
    rar_version=5,
    text_compress_opt_bool=False,
    work_dir="",
    rar_exe_file_dir="",
) -> str:
    if not isinstance(input_path_set, set):
        raise TypeError(
            f"type of input_path_set must be set "
            f"instead of {type(input_path_set)}"
        )

    if not input_path_set:
        return ""

    if not isinstance(output_dir, str):
        raise TypeError(
            f"type of output_dir must be str instead of {type(output_dir)}"
        )

    if not isinstance(output_filename, str):
        raise TypeError(
            f"type of output_filename must be str "
            f"instead of {type(output_filename)}"
        )

    if not isinstance(rar_exe_file_dir, str):
        raise TypeError(
            f"type of rar_exe_file_dir must be str "
            f"instead of {type(rar_exe_file_dir)}"
        )

    rar_exe_filename: str = "Rar.exe"
    if rar_exe_file_dir:
        if not os.path.isdir(rar_exe_file_dir):
            raise DirNotFoundError(
                f"rar dir cannot be found with {rar_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(rar_exe_file_dir)
        if rar_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{rar_exe_filename} cannot be found in " f"{rar_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({rar_exe_filename}):
            raise FileNotFoundError(
                f"{rar_exe_filename} cannot be found in environment path"
            )
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    rar_extension: str = ".rar"
    output_file_fullname: str = output_filename + rar_extension
    output_filepath: str = os.path.join(output_dir, output_file_fullname)

    if os.path.isfile(output_filepath):
        os.remove(output_filepath)

    rar_exe_filepath: str = os.path.join(rar_exe_file_dir, rar_exe_filename)
    add_key: str = "a"
    compress_level_key: str = f"-m{compress_level}"
    rar_version_key: str = f"-ma{rar_version}"
    black_hash_key: str = "-htb"

    text_compress_key: str = "-mct+"
    solid_compress_key: str = "-s"

    cmd_param_list: list = [rar_exe_filepath, add_key, output_filepath]
    cmd_param_list.extend(input_path_set)
    cmd_param_list += [compress_level_key, rar_version_key, black_hash_key]
    if solid_compress_bool:
        cmd_param_list.append(solid_compress_key)

    if text_compress_opt_bool:
        cmd_param_list.append(text_compress_key)

    rar_param_debug_str: str = (
        f"compress rar: param:" f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, rar_param_debug_str)
    print(rar_param_debug_str)

    start_info_str: str = f"compress rar: starting compress {output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process: subprocess.Popen = subprocess.Popen(cmd_param_list, cwd=work_dir)

    process.communicate()

    if process.returncode == 0:
        end_info_str: str = (
            f"compress rar: compress {input_path_set} to "
            f"{output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"compress rar: transcode {input_path_set} to "
            f"{output_filepath} unsuccessfully!"
        )

    return output_filepath


