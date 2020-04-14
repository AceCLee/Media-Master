"""
    ffprobe.py ffprobe module of media master
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

import os
import subprocess
import json
import logging
import sys

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def ffmpeg_probe(filepath: str, ffprobe_exe_file_dir=""):
    ffprobe_exe_filename = "ffprobe.exe"
    ffprobe_exe_filepath = os.path.join(
        ffprobe_exe_file_dir, ffprobe_exe_filename
    )
    args_list = [
        ffprobe_exe_filepath,
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        filepath,
    ]

    ffprobe_param_debug_str: str = (
        f"ffprobe: param: {subprocess.list2cmdline(args_list)}"
    )
    g_logger.log(logging.DEBUG, ffprobe_param_debug_str)

    process = subprocess.Popen(
        args_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout_data, stderr_data = process.communicate()

    return_code = process.returncode

    if return_code != 0:
        error_info_str: str = (
            f"ffprobe error:\n"
            f"stdout_data:\n"
            f"{stdout_data}"
            f"stderr_data:\n"
            f"{stderr_data}"
        )
        g_logger.log(logging.INFO, error_info_str)
        print(error_info_str, file=sys.stderr)
        raise ChildProcessError(error_info_str)

    return json.loads(stdout_data.decode("utf-8"))


