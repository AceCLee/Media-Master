"""
    multiplex.py multiplex media to video
    Copyright (C) 2019  Ace C Lee

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
import logging
import sys

from ..error import DirNotFoundError, RangeError
from ..util import check_file_environ_path

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def multiplex(
    track_info_list: list,
    output_file_dir: str,
    output_file_name: str,
    chapters_filepath="",
    attachments_filepath_set=set(),
    mkvmerge_exe_file_dir="",
) -> str:
    if not isinstance(track_info_list, list):
        raise TypeError(
            f"type of track_info_list must be list \
instead of {type(track_info_list)}"
        )

    if track_info_list and not isinstance(track_info_list[0], dict):
        raise TypeError(
            f"type of element of track_info_list must be dict \
instead of {type(track_info_list[0])}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str \
instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str \
instead of {type(output_file_name)}"
        )

    if not isinstance(chapters_filepath, str):
        raise TypeError(
            f"type of chapters_filepath must be str \
instead of {type(chapters_filepath)}"
        )

    if not isinstance(attachments_filepath_set, set):
        raise TypeError(
            f"type of attachments_filepath_set must be set \
instead of {type(attachments_filepath_set)}"
        )

    if not isinstance(mkvmerge_exe_file_dir, str):
        raise TypeError(
            f"type of mkvmerge_exe_file_dir must be str \
instead of {type(mkvmerge_exe_file_dir)}"
        )
    needed_key_set: set = {
        "filepath",
        "track_type",
        "sync_delay",
        "track_name",
        "language",
        "original_index",
    }
    available_track_type_set: set = {"video", "audio", "subtitle"}

    for infor_dict in track_info_list:
        key_set: set = set(infor_dict.keys())
        for key in key_set:
            if key not in needed_key_set:
                raise KeyError(f"{infor_dict} misses key {key}")

        filepath: str = infor_dict["filepath"]
        track_type: str = infor_dict["track_type"]
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"filepath of {infor_dict} cannot be found with \
{filepath}"
            )
        if track_type not in available_track_type_set:
            raise RangeError(
                message=f"value of track_type must in \
{available_track_type_set}",
                valid_range=str(available_track_type_set),
            )
    if chapters_filepath and not os.path.isfile(chapters_filepath):
        raise FileNotFoundError(
            f"input chapter file cannot be found with {filepath}"
        )
    if attachments_filepath_set:
        for filepath in attachments_filepath_set:
            if not os.path.isfile(filepath):
                raise FileNotFoundError(
                    f"input attachment file cannot be found with {filepath}"
                )

    mkvmerge_exe_filename: str = "mkvmerge.exe"
    if mkvmerge_exe_file_dir:
        if not os.path.isdir(mkvmerge_exe_file_dir):
            raise DirNotFoundError(
                f"mkvmerge dir cannot be found with {mkvmerge_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvmerge_exe_file_dir)
        if mkvmerge_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvmerge_exe_filename} cannot be found in \
{mkvmerge_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvmerge_exe_filename}):
            raise FileNotFoundError(
                f"{mkvmerge_exe_filename} cannot be found in \
environment path"
            )
    if not os.path.exists(output_file_dir):
        os.makedirs(output_file_dir)

    mkv_suffix: str = ".mkv"
    mkvmerge_exe_filepath: str = os.path.join(
        mkvmerge_exe_file_dir, mkvmerge_exe_filename
    )
    output_filename_fullname: str = output_file_name + mkv_suffix
    output_filepath: str = os.path.join(
        output_file_dir, output_filename_fullname
    )
    output_key: str = "--output"
    output_value: str = output_filepath
    audio_track_key: str = "--audio-tracks"
    video_track_key: str = "--video-tracks"
    subtitle_track_key: str = "--subtitle-tracks"
    no_audio_key: str = "--no-audio"
    no_video_key: str = "--no-video"
    no_subtitles_key: str = "--no-subtitles"
    no_attachments_key: str = "--no-attachments"
    sync_key: str = "--sync"
    track_name_key: str = "--track-name"
    language_key: str = "--language"
    cmd_param_list: list = [mkvmerge_exe_filepath, output_key, output_value]
    for track_info_dict in track_info_list:
        filepath: str = track_info_dict["filepath"]
        sync_delay: int = track_info_dict["sync_delay"]
        track_type: str = track_info_dict["track_type"]
        track_name: str = track_info_dict["track_name"]
        language: str = track_info_dict["language"]
        track_key: str = video_track_key if track_type == "video" else (
            audio_track_key if track_type == "audio" else subtitle_track_key
        )
        file_track_index: int = track_info_dict["original_index"]
        sync_value: str = f"{file_track_index}:{sync_delay}"
        track_cmd_param_list: list = [
            track_key,
            str(file_track_index),
            sync_key,
            sync_value,
        ]
        if track_type == "video":
            track_cmd_param_list += [
                no_audio_key,
                no_subtitles_key,
                no_attachments_key,
            ]
        elif track_type == "audio":
            track_cmd_param_list += [
                no_video_key,
                no_subtitles_key,
                no_attachments_key,
            ]
        elif track_type == "subtitle":
            track_cmd_param_list += [
                no_video_key,
                no_audio_key,
                no_attachments_key,
            ]
        if track_name:
            track_name_value: str = f"{file_track_index}:{track_name}"
            track_cmd_param_list += [track_name_key, track_name_value]
        if language:
            language_value: str = f"{file_track_index}:{language}"
            track_cmd_param_list += [language_key, language_value]
        track_cmd_param_list.append(filepath)
        cmd_param_list += track_cmd_param_list

    if chapters_filepath:
        chapters_key: str = "--chapters"
        chapters_value: str = chapters_filepath
        cmd_param_list += [chapters_key, chapters_value]

    if attachments_filepath_set:
        attachment_key: str = "--attach-file"
        for filepath in attachments_filepath_set:
            cmd_param_list += [attachment_key, filepath]

    mkvmerge_param_debug_str: str = f"multiplex mkvmerge: param:\
{subprocess.list2cmdline(cmd_param_list)}"
    g_logger.log(logging.DEBUG, mkvmerge_param_debug_str)

    start_info_str: str = f"multiplex mkvmerge: starting encapsulating \
{output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)
    
    
    process = subprocess.Popen(cmd_param_list)

    return_code = process.wait()

    if return_code == 0:
        end_info_str: str = f"multiplex mkvmerge: \
multiplex {output_filepath} successfully."
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"multiplex mkvmerge: \
multiplex {output_filepath} unsuccessfully."
        )

    return output_filepath


