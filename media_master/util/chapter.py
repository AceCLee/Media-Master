"""
    chapter.py chapter module of media_master
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

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def get_chapter_format_info_dict():
    return dict(
        ogm=dict(ext=".txt", cmd_format="ogm"),
        pot=dict(ext=".pbf", cmd_format="pot"),
        simple=dict(ext=".txt", cmd_format="simple"),
        tab=dict(ext=".txt", cmd_format="tab"),
        matroska=dict(ext=".xml", cmd_format="xml"),
    )


def convert_chapter_format(
    src_chapter_filepath: str,
    output_dir: str,
    output_filename: str,
    dst_chapter_format: str,
) -> str:
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    all_format_info_dict: dict = dict(
        ogm=dict(ext=".txt", cmd_format="ogm"),
        pot=dict(ext=".pbf", cmd_format="pot"),
        simple=dict(ext=".txt", cmd_format="simple"),
        tab=dict(ext=".txt", cmd_format="tab"),
        matroska=dict(ext=".xml", cmd_format="xml"),
    )

    chapter_converter_py_filepath: str = "media_master/util/chapter_converter.py"

    format_info: dict = all_format_info_dict[dst_chapter_format]

    src_full_filename: str = os.path.basename(src_chapter_filepath)

    src_filename, src_extension = os.path.splitext(src_full_filename)

    dst_full_filename: str = output_filename + format_info["ext"]

    dst_filepath: str = os.path.join(output_dir, dst_full_filename)

    if os.path.isfile(dst_filepath):
        os.remove(dst_filepath)

    python_exe = "python.exe"

    cmd_param_list: list = [
        python_exe,
        chapter_converter_py_filepath,
        "--format",
        format_info["cmd_format"],
        "--output",
        dst_filepath,
        src_chapter_filepath,
    ]

    param_debug_str: str = (
        f"convert_chapter_format: param: {subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, param_debug_str)
    print(param_debug_str, file=sys.stderr)

    start_info_str: str = (
        f"convert_chapter_format: "
        f"start convert {src_chapter_filepath} "
        f"to {dst_filepath}"
    )

    g_logger.log(logging.INFO, start_info_str)
    print(start_info_str, file=sys.stderr)

    process: subprocess.Popen = subprocess.Popen(cmd_param_list)

    process.communicate()

    return_code = process.returncode

    if return_code == 0:
        end_info_str: str = (
            f"convert_chapter_format: "
            f"start convert {src_chapter_filepath} "
            f"to {dst_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"convert_chapter_format: "
            f"start convert {src_chapter_filepath} "
            f"to {dst_filepath} unsuccessfully."
        )

    return dst_filepath


