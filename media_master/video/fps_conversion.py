"""
    fps_conversion.py convert fps of video stream
    Copyright (C) 2020  Ace C Lee

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import os
import subprocess
import sys

from ..error import DirNotFoundError, MissTemplateError, RangeError
from ..util import check_file_environ_path

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def avc_fps_conversion(
    filepath: str,
    ouput_dir: str,
    output_filename: str,
    output_fps: str,
    mkvmerge_exe_file_dir="",
):
    mkv_extension: str = ".mkv"
    if not os.path.isdir(ouput_dir):
        os.makedirs(ouput_dir)
    output_full_filename: str = output_filename + mkv_extension
    output_filepath: str = os.path.join(ouput_dir, output_full_filename)

    mkvmerge_exe_filename: str = "mkvmerge.exe"
    if mkvmerge_exe_file_dir:
        if not os.path.isdir(mkvmerge_exe_file_dir):
            raise DirNotFoundError(
                f"mkvmerge dir cannot be found with {mkvmerge_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvmerge_exe_file_dir)
        if mkvmerge_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvmerge_exe_filename} cannot be found in "
                f"{mkvmerge_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvmerge_exe_filename}):
            raise FileNotFoundError(
                f"{mkvmerge_exe_filename} cannot be found in "
                "environment path"
            )
    if not os.path.exists(ouput_dir):
        os.makedirs(ouput_dir)

    mkvmerge_exe_filepath: str = os.path.join(
        mkvmerge_exe_file_dir, mkvmerge_exe_filename
    )
    output_key: str = "--output"
    output_value: str = output_filepath
    default_index: int = 0
    default_deration_key: str = "--default-duration"
    default_deration_value: str = f"{default_index}:{output_fps}fps"
    fix_timing_info_key: str = "--fix-bitstream-timing-information"

    cmd_param_list: list = [
        mkvmerge_exe_filepath,
        output_key,
        output_value,
        default_deration_key,
        default_deration_value,
        fix_timing_info_key,
        str(default_index),
        filepath,
    ]
    print(cmd_param_list, file=sys.stderr)

    mkvmerge_param_debug_str: str = (
        f"multiplex mkvmerge: param:"
        f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    print(mkvmerge_param_debug_str, file=sys.stderr)
    g_logger.log(logging.DEBUG, mkvmerge_param_debug_str)

    start_info_str: str = (
        f"multiplex mkvmerge: starting multiplexing {output_filepath}"
    )

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)
    process = subprocess.Popen(
        cmd_param_list,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    stdout_lines: list = []
    while process.poll() is None:
        stdout_line = process.stdout.readline()
        stdout_lines.append(stdout_line)
        print(stdout_line, end="", file=sys.stderr)

    return_code = process.returncode

    if return_code == 0:
        end_info_str: str = (
            f"multiplex mkvmerge: "
            f"multiplex {output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    elif return_code == 1:
        warning_prefix = "Warning:"
        warning_text_str = "".join(
            line for line in stdout_lines if line.startswith(warning_prefix)
        )
        stdout_text_str = "".join(stdout_lines)
        warning_str: str = (
            "multiplex mkvmerge: "
            "mkvmerge has output at least one warning, "
            "but muxing did continue.\n"
            f"warning:\n{warning_text_str}"
            f"stdout:\n{stdout_text_str}"
        )
        print(warning_str, file=sys.stderr)
        g_logger.log(logging.WARNING, warning_str)
    else:
        error_str = (
            f"multiplex mkvmerge: "
            f"multiplex {output_filepath} unsuccessfully."
        )
        print(error_str, file=sys.stderr)
        raise subprocess.CalledProcessError(
            returncode=return_code,
            cmd=subprocess.list2cmdline(cmd_param_list),
            output=stdout_text_str,
        )

    return output_filepath


def dir_avc_fps_conversion(
    input_dir: str, output_fps: str, output_filename_suffix="_fps_revise"
):
    video_extension_set: set = {".mkv", ".mp4"}
    video_filename_set: set = set()
    for full_filename in os.listdir(input_dir):
        filename, extension = os.path.splitext(full_filename)
        if extension in video_extension_set:
            video_filename_set.add(full_filename)

    for full_filename in video_filename_set:
        input_filepath = os.path.join(input_dir, full_filename)
        print(input_filepath)
        filename, extension = os.path.splitext(full_filename)
        new_filename = filename + output_filename_suffix
        print(new_filename)
        avc_fps_conversion(
            filepath=input_filepath,
            ouput_dir=input_dir,
            output_filename=new_filename,
            output_fps=output_fps,
        )


