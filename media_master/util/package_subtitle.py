"""
    package_subtitle.py package subtitle to video file
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
import re
import subprocess
import sys

from ..error import DirNotFoundError, RangeError
from ..util import check_file_environ_path

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def package_subtitle_2_mkv(
    video_filepath: str,
    subtitle_filepath: str,
    subtitle_title: str,
    subtitle_language: str,
    output_dir: str,
    output_filename: str,
    mkvmerge_exe_file_dir="",
):
    mkv_extension: str = ".mkv"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    output_full_filename: str = output_filename + mkv_extension
    output_filepath: str = os.path.join(output_dir, output_full_filename)

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
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mkvmerge_exe_filepath: str = os.path.join(
        mkvmerge_exe_file_dir, mkvmerge_exe_filename
    )
    output_key: str = "--output"
    output_value: str = output_filepath

    track_name_key: str = "--track-name"
    language_key: str = "--language"

    cmd_param_list: list = [
        mkvmerge_exe_filepath,
        output_key,
        output_value,
        video_filepath,
    ]

    track_name_value: str = f"0:{subtitle_title}"
    cmd_param_list += [track_name_key, track_name_value]
    language_value: str = f"0:{subtitle_language}"
    cmd_param_list += [language_key, language_value]

    cmd_param_list.append(subtitle_filepath)

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
        cmd_param_list, stdout=subprocess.PIPE, text=True, encoding="utf-8"
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


def package_subtitles(
    output_dir: str,
    video_dir: str,
    video_filename_re_exp: str,
    subtitle_dir: str,
    subtitle_filename_re_exp: str,
    subtitle_title: str,
    subtitle_language: str,
):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    video_filename_re_pattern = re.compile(video_filename_re_exp)
    subtitle_filename_re_pattern = re.compile(subtitle_filename_re_exp)
    video_filename_list: list = [
        filename
        for filename in os.listdir(video_dir)
        if os.path.isfile(os.path.join(video_dir, filename))
        and video_filename_re_pattern.search(filename)
    ]
    subtitle_filename_list: list = [
        filename
        for filename in os.listdir(subtitle_dir)
        if os.path.isfile(os.path.join(subtitle_dir, filename))
        and subtitle_filename_re_pattern.search(filename)
    ]
    if len(video_filename_list) != len(subtitle_filename_list):
        raise ValueError(
            f"len(video_filename_list) != "
            f"len(subtitle_filename_list): "
            f"{len(video_filename_list)} != "
            f"{len(subtitle_filename_list)}"
        )
    for video_filename in video_filename_list:
        video_episode_num = int(
            video_filename_re_pattern.search(video_filename).group(1)
        )
        for subtitle_filename in subtitle_filename_list:
            subtitle_episode_num = int(
                subtitle_filename_re_pattern.search(subtitle_filename).group(1)
            )
            if video_episode_num != subtitle_episode_num:
                continue
            package_subtitle_2_mkv(
                video_filepath=os.path.join(video_dir, video_filename),
                subtitle_filepath=os.path.join(
                    subtitle_dir, subtitle_filename
                ),
                subtitle_title=subtitle_title,
                subtitle_language=subtitle_language,
                output_dir=output_dir,
                output_filename=os.path.splitext(video_filename)[0],
            )


