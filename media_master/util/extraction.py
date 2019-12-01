"""
    extraction.py extract media track of video
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

import logging
import os
import subprocess
import sys
from xml.dom import minidom
import re

from pymediainfo import MediaInfo

from ..track import (
    VideoTrackFile,
    AudioTrackFile,
    TextTrackFile,
    MenuTrackFile,
)
from ..error import DirNotFoundError, RangeError
from .check import check_file_environ_path
from .multiplex import multiplex
from .meta_data import get_proper_frame_rate, reliable_meta_data

import shutil

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def split_mediainfo_str2list(string: str) -> list:
    return string.split(sep=" / ")


def get_stream_order(streamorder_str: str) -> int:
    if isinstance(streamorder_str, str):
        if "-" in streamorder_str:
            streamorder_str: str = streamorder_str[
                streamorder_str.index("-") + 1 :
            ]
            streamorder: int = int(streamorder_str)
        else:
            streamorder: int = int(streamorder_str)
    else:
        raise RuntimeError(
            f"Unknown streamorder: {streamorder_str} "
            f"type:{type(streamorder_str)}"
        )
    return streamorder


def extract_track_ffmpeg(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    output_file_suffix: str,
    track_type: str,
    stream_identifier=0,
    ffmpeg_exe_file_dir="",
) -> str:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
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

    if not isinstance(output_file_suffix, str):
        raise TypeError(
            f"type of output_file_suffix must be str \
instead of {type(output_file_suffix)}"
        )

    if not isinstance(track_type, str):
        raise TypeError(
            f"type of track_type must be str \
instead of {type(track_type)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str \
instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    ffmpeg_exe_filename: str = "ffmpeg.exe"
    if ffmpeg_exe_file_dir:
        if not os.path.isdir(ffmpeg_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {ffmpeg_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(ffmpeg_exe_file_dir)
        if ffmpeg_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
environment path"
            )

    video_type: str = "video"
    audio_type: str = "audio"
    subtitle_type: str = "subtitle"
    available_type_set: set = {video_type, audio_type, subtitle_type}
    if track_type not in available_type_set:
        raise RangeError(
            message=f"value of track_type must in {available_type_set}",
            valid_range=str(available_type_set),
        )
    if not os.path.exists(output_file_dir):
        os.makedirs(output_file_dir)

    track_suffix: str = output_file_suffix.replace(".", "")

    output_file_fullname: str = f"{output_file_name}_\
{track_type}.{track_suffix}"

    output_filepath: str = os.path.join(output_file_dir, output_file_fullname)

    if os.path.isfile(output_filepath):
        skip_info_str: str = f"extraction ffmpeg: {output_filepath} \
already existed, skip extraction."

        print(skip_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, skip_info_str)
        return output_filepath

    ffmpeg_exe_filepath: str = os.path.join(
        ffmpeg_exe_file_dir, ffmpeg_exe_filename
    )
    input_key: str = "-i"
    input_value: str = input_filepath
    overwrite_key: str = "-y"
    codec_key: str = "-codec"
    codec_value: str = "copy"
    map_key: str = "-map"
    map_video_symbol: str = "v"
    map_audio_symbol: str = "a"
    map_subtitle_symbol: str = "s"
    no_video_key: str = "-vn"
    no_audio_key: str = "-an"
    no_subtitle_key: str = "-sn"
    no_data_key: str = "-dn"
    type_symbol: str = ""

    if track_type == video_type:
        type_symbol = map_video_symbol
    elif track_type == audio_type:
        type_symbol = map_audio_symbol
    elif track_type == subtitle_type:
        type_symbol = map_subtitle_symbol
    else:
        raise RuntimeError("It's impossible to execute this code.")

    map_value = f"0:{type_symbol}:{stream_identifier}"
    output_value = output_filepath

    args_list: list = [
        ffmpeg_exe_filepath,
        input_key,
        input_value,
        overwrite_key,
        codec_key,
        codec_value,
        map_key,
        map_value,
        output_value,
    ]

    ffmpeg_param_debug_str: str = (
        f"extraction ffmpeg: param:{subprocess.list2cmdline(args_list)}"
    )
    g_logger.log(logging.DEBUG, ffmpeg_param_debug_str)

    start_info_str: str = (
        f"extraction ffmpeg: starting extracting {output_filepath}"
    )

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)
    
    
    process = subprocess.Popen(args_list)

    return_code = process.wait()

    if return_code == 0:
        end_info_str: str = f"extraction ffmpeg: \
extract {output_filepath} successfully."
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"extraction ffmpeg: \
extract {output_filepath} unsuccessfully."
        )

    return output_filepath


def extract_track_mkvextract(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    output_file_suffix: str,
    track_type: str,
    track_index: int,
    mkvextract_exe_file_dir="",
) -> str:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
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

    if not isinstance(output_file_suffix, str):
        raise TypeError(
            f"type of output_file_suffix must be str \
instead of {type(output_file_suffix)}"
        )

    if not isinstance(track_type, str):
        raise TypeError(
            f"type of track_type must be str \
instead of {type(track_type)}"
        )

    if not isinstance(track_index, int):
        raise TypeError(
            f"type of track_index must be int \
instead of {type(track_index)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str \
instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkv_suffix: str = ".mkv"
    if not input_filepath.endswith(mkv_suffix):
        raise TypeError(
            f"format of input_filepath must be Matroska \
and it has to end with {mkv_suffix}"
        )

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"mkvextract dir cannot be found with \
{mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
environment path"
            )

    video_type: str = "video"
    audio_type: str = "audio"
    text_type: str = "text"
    available_type_set: set = {video_type, audio_type, text_type}
    if track_type not in available_type_set:
        raise RangeError(
            message=f"value of track_type must in {available_type_set}",
            valid_range=str(available_type_set),
        )
    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    min_index: int = 0
    max_index: int = len(media_info_list) - 2
    if track_index < min_index or track_index > max_index:
        raise RangeError(
            message=f"value of track_index must in [{min_index},{max_index}]",
            valid_range=f"[{min_index},{max_index}]",
        )
    index_track_info_dict: dict = next(
        track_info
        for track_info in media_info_list[1:]
        if track_info["streamorder"] == str(track_index)
    )
    index_track_type: str = index_track_info_dict["track_type"].lower()
    if index_track_type != track_type:
        raise ValueError(
            f"stream in {track_index} track is not {track_type} \
but {index_track_type} "
        )
    if not os.path.exists(output_file_dir):
        os.makedirs(output_file_dir)
    
    
    
    
    

    track_suffix: str = output_file_suffix.replace(".", "")

    output_file_fullname: str = f"{output_file_name}_index_\
{track_index}.{track_suffix}"

    output_filepath: str = os.path.join(output_file_dir, output_file_fullname)

    if os.path.isfile(output_filepath):
        skip_info_str: str = f"extraction mkvextract: {output_filepath} \
already existed, skip extraction."

        print(skip_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, skip_info_str)
        return output_filepath

    mkvextract_exe_filepath: str = os.path.join(
        mkvextract_exe_file_dir, mkvextract_exe_filename
    )

    input_value: str = input_filepath
    track_type_param = "tracks"
    output_value: str = f"{track_index}:{output_filepath}"

    args_list: list = [
        mkvextract_exe_filepath,
        input_value,
        track_type_param,
        output_value,
    ]

    opus_param_debug_str: str = f"extraction mkvextract: param:\
{subprocess.list2cmdline(args_list)}"
    g_logger.log(logging.DEBUG, opus_param_debug_str)

    start_info_str: str = f"extraction mkvextract: starting extracting \
{output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)
    
    
    process = subprocess.Popen(args_list)

    return_code = process.wait()

    if return_code == 0:
        end_info_str: str = f"extraction mkvextract: \
extract {output_filepath} successfully."
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"extraction mkvextract: \
extract {output_filepath} unsuccessfully."
        )

    return output_filepath


def extract_all_subtitles(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    mkvextract_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> list:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
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
    
    

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str \
instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )
    
    
    
    

    mkv_suffix: str = ".mkv"

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"mkvextract dir cannot be found with \
{mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
environment path"
            )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str \
instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    ffmpeg_exe_filename: str = "ffmpeg.exe"
    if ffmpeg_exe_file_dir:
        if not os.path.isdir(ffmpeg_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {ffmpeg_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(ffmpeg_exe_file_dir)
        if ffmpeg_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
environment path"
            )
    if not os.path.isdir(output_file_dir):
        os.makedirs(output_file_dir)

    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    text_info_list: list = [
        track
        for track in media_info_list
        if track["track_type"].lower() == "text"
    ]
    if not text_info_list:
        return tuple()

    text_key: str = "tracks"

    text_track_file_list: list = []
    for text_track_index, text_info_dict in enumerate(text_info_list):
        track_index: int = get_stream_order(text_info_dict["streamorder"])

        text_format: str = text_info_dict["format"].lower()
        track_suffix: str = text_format
        if text_format == "pgs":
            track_suffix = "sup"

        if input_filepath.endswith(mkv_suffix):
            output_filename: str = (
                f"{output_file_name}_index_{track_index}.{track_suffix}"
            )
            output_filepath: str = os.path.join(
                output_file_dir, output_filename
            )
            mkvextract_exe_filepath: str = os.path.join(
                mkvextract_exe_file_dir, mkvextract_exe_filename
            )

            text_key: str = "tracks"
            text_value: str = f"{track_index}:{output_filepath}"

            mkvextract_cmd_param_list: list = [
                mkvextract_exe_filepath,
                input_filepath,
                text_key,
                text_value,
            ]

            param_debug_str: str = (
                f"extraction text: param:"
                f"{subprocess.list2cmdline(mkvextract_cmd_param_list)}"
            )
            g_logger.log(logging.DEBUG, param_debug_str)

            start_info_str: str = (
                f"extraction text: "
                f"start extract {output_filepath} from {input_filepath}"
            )
            print(start_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, start_info_str)

            process: subprocess.Popen = subprocess.Popen(
                mkvextract_cmd_param_list
            )

            return_code: int = process.wait()

            if return_code == 0:
                end_info_str: str = (
                    f"extraction text: extract "
                    f"{output_filepath} from {input_filepath} successfully."
                )
                print(end_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, end_info_str)
            else:
                raise ChildProcessError(
                    f"extraction text: extract {output_filepath} "
                    f"from {input_filepath} unsuccessfully!"
                )

        else:
            output_filepath: str = extract_track_ffmpeg(
                input_filepath,
                output_file_dir=output_file_dir,
                output_file_name=output_file_name,
                output_file_suffix=track_suffix,
                track_type="subtitle",
                stream_identifier=int(text_info_dict["stream_identifier"]),
                ffmpeg_exe_file_dir=ffmpeg_exe_file_dir,
            )

        text_track_file: TextTrackFile = TextTrackFile(
            filepath=output_filepath,
            track_index=track_index,
            track_format=text_info_dict["format"].lower(),
            duration_ms=int(float(text_info_dict["duration"]))
            if "duration" in text_info_dict
            else -1,
            bit_rate_bps=int(text_info_dict["bit_rate"])
            if "bit_rate" in text_info_dict
            else -1,
            delay_ms=int(float(text_info_dict["delay"]))
            if "delay" in text_info_dict
            else 0,
            stream_size_byte=int(text_info_dict["stream_size"])
            if "stream_size" in text_info_dict
            else -1,
            title=text_info_dict["title"]
            if "title" in text_info_dict.keys()
            else "",
            language=text_info_dict["language"]
            if "language" in text_info_dict.keys()
            else "",
            default_bool=False
            if "default" not in text_info_dict.keys()
            else (
                True if text_info_dict["default"].lower() == "yes" else False
            ),
            forced_bool=False
            if "default" not in text_info_dict.keys()
            else (
                True if text_info_dict["forced"].lower() == "yes" else False
            ),
        )
        text_track_file_list.append(text_track_file)

    return text_track_file_list


def extract_all_attachments(
    input_filepath: str, output_file_dir: str, mkvextract_exe_file_dir=""
) -> tuple:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str \
instead of {type(output_file_dir)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str \
instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkv_suffix: str = ".mkv"
    if not input_filepath.endswith(mkv_suffix):
        raise TypeError(
            f"format of input_filepath must be Matroska \
and it has to end with {mkv_suffix}"
        )

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
environment path"
            )
    if not os.path.isdir(output_file_dir):
        os.makedirs(output_file_dir)

    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    general_info_dict: dict = next(
        (
            track
            for track in media_info_list
            if track["track_type"] == "General"
        ),
        None,
    )

    attachment_key: str = "attachments"
    general_info_key_set: set = set(general_info_dict.keys())
    if attachment_key not in general_info_key_set:
        return tuple()
    attachment_filename_list: list = split_mediainfo_str2list(
        general_info_dict[attachment_key]
    )

    output_attachment_filepath_list: list = [
        os.path.join(output_file_dir, filename)
        for filename in attachment_filename_list
    ]

    mkvextract_exe_filepath: str = os.path.join(
        mkvextract_exe_file_dir, mkvextract_exe_filename
    )

    attachment_key: str = "attachments"
    attachment_value_template: str = "{attachment_id}:{output_path}"

    mkvextract_param_list: list = [
        mkvextract_exe_filepath,
        input_filepath,
        attachment_key,
    ]

    for index, filepath in enumerate(output_attachment_filepath_list):
        mkvextract_param_list.append(
            attachment_value_template.format(
                attachment_id=index + 1, output_path=filepath
            )
        )

    param_debug_str: str = f"extraction attachment: param:\
{subprocess.list2cmdline(mkvextract_param_list)}"
    g_logger.log(logging.DEBUG, param_debug_str)

    start_info_str: str = f"extraction attachment: \
start extract {attachment_filename_list} \
from {input_filepath}"
    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process: subprocess.Popen = subprocess.Popen(mkvextract_param_list)

    return_code: int = process.wait()

    if return_code == 0:
        end_info_str: str = f"extraction attachment: \
extract {attachment_filename_list} \
from {input_filepath} successfully."
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"extraction attachment: \
extract {attachment_filename_list} \
from {input_filepath} unsuccessfully!"
        )

    return tuple(output_attachment_filepath_list)


def extract_chapter(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    mkvextract_exe_file_dir="",
) -> MenuTrackFile:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
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

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str \
instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
environment path"
            )
    if not os.path.isdir(output_file_dir):
        os.makedirs(output_file_dir)

    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    menu_track_type: str = "Menu"
    menu_info_list: list = [
        track
        for track in media_info_list
        if track["track_type"] == menu_track_type
    ]
    if not menu_info_list:
        return

    output_file_fullname: str = f"{output_file_name}.xml"
    output_filepath: str = os.path.join(output_file_dir, output_file_fullname)

    mkv_suffix: str = ".mkv"
    if input_filepath.endswith(mkv_suffix):
        mkvextract_exe_filepath: str = os.path.join(
            mkvextract_exe_file_dir, mkvextract_exe_filename
        )

        menu_key: str = "chapters"
        menu_value: str = output_filepath

        mkvextract_param_list: list = [
            mkvextract_exe_filepath,
            input_filepath,
            menu_key,
            menu_value,
        ]

        param_debug_str: str = f"extraction menu: param:\
{subprocess.list2cmdline(mkvextract_param_list)}"
        g_logger.log(logging.DEBUG, param_debug_str)

        start_info_str: str = f"extraction menu: \
start extract {output_file_fullname} \
from {input_filepath}"
        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        process: subprocess.Popen = subprocess.Popen(mkvextract_param_list)

        return_code: int = process.wait()

        if return_code == 0:
            end_info_str: str = f"extraction menu: \
extract {output_file_fullname} \
from {input_filepath} successfully."
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)
        else:
            raise ChildProcessError(
                f"extraction menu: \
extract {output_file_fullname} \
from {input_filepath} unsuccessfully!"
            )
    else:
        menu_info_dict: dict = menu_info_list[0]
        time_re_exp: str = "(\\d{2})_(\\d{2})_(\\d{2})(\\d{3})"
        chapter_info_list: list = []
        for key in menu_info_dict.keys():
            re_result = re.search(time_re_exp, key)
            if not re_result:
                continue
            start_time: str = f"{re_result.group(1)}:{re_result.group(2)}:\
{re_result.group(3)}.{re_result.group(4)}"
            chapter_name: str = menu_info_dict[key]
            chapter_info_list.append(
                dict(start_time=start_time, chapter_name=chapter_name)
            )
        chapter_info_list.sort(key=lambda element: element["start_time"])
        chapters_xml = minidom.Document()

        chapters_node = chapters_xml.createElement("Chapters")
        chapters_xml.appendChild(chapters_node)
        edition_entry_node = chapters_xml.createElement("EditionEntry")
        chapters_node.appendChild(edition_entry_node)
        for chapter_info in chapter_info_list:
            chapter_atom_node = chapters_xml.createElement("ChapterAtom")
            edition_entry_node.appendChild(chapter_atom_node)

            chapter_time_start_node = chapters_xml.createElement(
                "ChapterTimeStart"
            )
            chapter_atom_node.appendChild(chapter_time_start_node)

            text_node = chapters_xml.createTextNode(chapter_info["start_time"])
            chapter_time_start_node.appendChild(text_node)

            chapter_display_node = chapters_xml.createElement("ChapterDisplay")
            chapter_atom_node.appendChild(chapter_display_node)

            chapter_string_node = chapters_xml.createElement("ChapterString")
            chapter_display_node.appendChild(chapter_string_node)

            text_node = chapters_xml.createTextNode(
                chapter_info["chapter_name"]
            )
            chapter_string_node.appendChild(text_node)

        with open(output_filepath, "w", encoding="utf-8") as xml_file:
            xml_file.write(chapters_xml.toprettyxml())

    return MenuTrackFile(filepath=output_filepath)


def extract_audio_track(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    audio_track: str,
    mkvextract_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> list:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
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

    if not isinstance(audio_track, str):
        raise TypeError(
            f"type of audio_track must be str \
instead of {type(audio_track)}"
        )
    
    

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str \
instead of {type(mkvextract_exe_file_dir)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str \
instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    available_track_type_set: set = {"default", "all"}
    if audio_track not in available_track_type_set:
        raise RangeError(
            message=f"value of audio_track must in {available_track_type_set}",
            valid_range=str(available_track_type_set),
        )
    
    

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
environment path"
            )

    ffmpeg_exe_filename: str = "ffmpeg.exe"
    if ffmpeg_exe_file_dir:
        if not os.path.isdir(ffmpeg_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {ffmpeg_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(ffmpeg_exe_file_dir)
        if ffmpeg_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
environment path"
            )

    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    audio_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Audio"),
        None,
    )

    audio_track_cnt: int = 0
    audio_track_file_list: list = []
    for audio_info_dict in media_info_list:
        if audio_info_dict["track_type"] != "Audio":
            continue
        audio_track_cnt += 1

        audio_info_key_set: set = set(audio_info_dict.keys())

        delay_key: str = "delay"

        delay_ms: int = 0

        if delay_key in audio_info_key_set:
            delay_ms = int(float(audio_info_dict[delay_key]))

        mkv_suffix: str = ".mkv"
        mkv_bool: bool = input_filepath.endswith(mkv_suffix)

        audio_format: str = audio_info_dict["format"].lower()
        

        track_suffix: str = audio_format
        if audio_format == "mpeg audio":
            print(audio_info_dict)
            if "format_profile" in audio_info_dict.keys():
                format_profile = audio_info_dict["format_profile"].lower()
                if format_profile == "layer 3":
                    track_suffix = "mp3"
                elif format_profile == "layer 2":
                    track_suffix = "mp2"
                else:
                    raise RuntimeError(
                        f"Unknown format_profile: {format_profile}"
                    )
            else:
                if audio_info_dict["codec_id_hint"].lower() == "mp3":
                    track_suffix = "mp3"
                else:
                    raise RuntimeError(
                        f"Unknown codec_id_hint: "
                        f"{audio_info_dict['codec_id_hint']}"
                    )
        elif audio_format == "e-ac-3":
            track_suffix = "ac3"
        elif audio_format == "pcm":
            track_suffix = "wav"

        output_filepath: str = ""
        if mkv_bool:
            audio_index: int = int(audio_info_dict["streamorder"])
            output_filepath = extract_track_mkvextract(
                input_filepath,
                output_file_dir,
                output_file_name,
                track_suffix,
                "audio",
                audio_index,
                mkvextract_exe_file_dir,
            )
        else:
            output_filepath = extract_track_ffmpeg(
                input_filepath,
                output_file_dir,
                output_file_name,
                track_suffix,
                "audio",
                ffmpeg_exe_file_dir,
            )

        audio_track_file: AudioTrackFile = AudioTrackFile(
            filepath=output_filepath,
            track_index=get_stream_order(audio_info_dict["streamorder"]),
            track_format=audio_info_dict["format"].lower(),
            duration_ms=int(float(audio_info_dict["duration"]))
            if "duration" in audio_info_dict.keys()
            else -1,
            bit_rate_bps=int(audio_info_dict["bit_rate"])
            if "bit_rate" in audio_info_dict.keys()
            else -1,
            bit_depth=int(audio_info_dict["bit_depth"])
            if "bit_depth" in audio_info_dict.keys()
            else -1,
            delay_ms=delay_ms,
            stream_size_byte=int(audio_info_dict["stream_size"])
            if "stream_size" in audio_info_dict.keys()
            else -1,
            title=audio_info_dict["title"]
            if "title" in audio_info_dict.keys()
            else "",
            language=audio_info_dict["language"]
            if "language" in audio_info_dict.keys()
            else "",
            default_bool=True
            if "default" not in audio_info_dict.keys()
            else (
                True if audio_info_dict["default"].lower() == "yes" else False
            ),
            forced_bool=True
            if "forced" not in audio_info_dict.keys()
            else (
                True if audio_info_dict["forced"].lower() == "yes" else False
            ),
        )
        audio_track_file_list.append(audio_track_file)
        if audio_track == "default" and audio_track_cnt == 1:
            break

    return audio_track_file_list


def extract_video_track(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    
    mkvextract_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> VideoTrackFile:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
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
    
    

    
    

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str \
instead of {type(mkvextract_exe_file_dir)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str \
instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in \
environment path"
            )

    ffmpeg_exe_filename: str = "ffmpeg.exe"
    if ffmpeg_exe_file_dir:
        if not os.path.isdir(ffmpeg_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {ffmpeg_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(ffmpeg_exe_file_dir)
        if ffmpeg_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in \
environment path"
            )

    media_info_data: dict = MediaInfo.parse(input_filepath).to_data()
    media_info_list: list = media_info_data["tracks"]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )

    video_info_key_set: set = set(video_info_dict.keys())

    cache_mkv_filename: str = output_file_name + "_new"
    cache_mkv_filepath: str = ""
    unreliable_meta_data_bool: bool = not reliable_meta_data(media_info_data)
    if unreliable_meta_data_bool:
        cache_mkv_filepath = multiplex(
            track_info_list=[
                dict(
                    filepath=input_filepath,
                    sync_delay=0,
                    track_type="video",
                    track_name="",
                    language="",
                    original_index=int(video_info_dict["streamorder"]),
                )
            ],
            output_file_dir=output_file_dir,
            output_file_name=cache_mkv_filename,
        )
        input_filepath = cache_mkv_filepath

    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )

    video_info_key_set: set = set(video_info_dict.keys())

    play_frame_rate: str = get_proper_frame_rate(
        video_info_dict=video_info_dict,
        video_info_key_set=video_info_key_set,
        
        original_fps=False if unreliable_meta_data_bool else True,
    )
    if not play_frame_rate:
        raise KeyError(
            f"video track of {input_filepath} "
            f"does not have frame_rate info."
        )

    color_range_key: str = "color_range"
    if color_range_key in video_info_key_set:
        color_range: str = video_info_dict[color_range_key].lower()
    else:
        color_range: str = "limited"

    mkv_suffix: str = ".mkv"
    mp4_suffix: str = ".mp4"
    m4v_suffix: str = ".m4v"
    flv_suffix: str = ".flv"
    mkv_bool: bool = input_filepath.endswith(mkv_suffix)
    mp4_bool: bool = input_filepath.endswith(mp4_suffix)
    m4v_bool: bool = input_filepath.endswith(m4v_suffix)
    flv_bool: bool = input_filepath.endswith(flv_suffix)

    video_format: str = video_info_dict["format"].lower()

    if video_format == "hevc":
        track_suffix: str = "265"
    elif video_format == "avc":
        track_suffix: str = "264"
    elif video_format == "mpeg-4 visual":
        track_suffix: str = "263"
    else:
        raise RuntimeError(f"unknown video format:{video_format}")

    if mp4_bool:
        track_suffix = mp4_suffix
    elif flv_bool:
        track_suffix = flv_suffix
    elif m4v_bool:
        track_suffix = mp4_suffix

    output_filepath: str = ""
    if mkv_bool:
        video_index: int = int(video_info_dict["streamorder"])
        output_filepath = extract_track_mkvextract(
            input_filepath,
            output_file_dir,
            output_file_name,
            track_suffix,
            "video",
            video_index,
            mkvextract_exe_file_dir,
        )
    else:
        output_filepath = extract_track_ffmpeg(
            input_filepath,
            output_file_dir,
            output_file_name,
            track_suffix,
            "video",
            ffmpeg_exe_file_dir,
        )

    video_track_file: VideoTrackFile = VideoTrackFile(
        filepath=output_filepath,
        track_index=int(video_info_dict["streamorder"]),
        track_format=video_info_dict["format"].lower(),
        duration_ms=int(float(video_info_dict["duration"])),
        bit_rate_bps=int(video_info_dict["bit_rate"])
        if "bit_rate" in video_info_dict.keys()
        else -1,
        width=video_info_dict["width"],
        height=video_info_dict["height"],
        frame_rate=play_frame_rate,
        frame_count=int(video_info_dict["frame_count"]),
        color_range=color_range,
        color_space=video_info_dict["color_space"],
        chroma_subsampling=video_info_dict["chroma_subsampling"],
        bit_depth=int(video_info_dict["bit_depth"]),
        delay_ms=int(video_info_dict["delay"])
        if "delay" in video_info_dict.keys()
        else 0,
        stream_size_byte=int(video_info_dict["stream_size"])
        if "stream_size" in video_info_dict.keys()
        else -1,
        title=video_info_dict["title"]
        if "title" in video_info_dict.keys()
        else "",
        language=video_info_dict["language"]
        if "language" in video_info_dict.keys()
        else "",
        default_bool=True
        if "default" not in video_info_dict.keys()
        else (True if video_info_dict["default"].lower() == "yes" else False),
        forced_bool=True
        if "forced" not in video_info_dict.keys()
        else (True if video_info_dict["forced"].lower() == "yes" else False),
    )

    if cache_mkv_filepath:
        delete_info_str: str = f"delete cache mkv {cache_mkv_filepath}"
        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(cache_mkv_filepath)

    return video_track_file


def copy_video(input_filepath: str, output_file_dir: str) -> VideoTrackFile:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str \
instead of {type(output_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    media_info_data: dict = MediaInfo.parse(input_filepath).to_data()
    media_info_list: list = media_info_data["tracks"]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )

    video_info_key_set: set = set(video_info_dict.keys())

    input_filename: str = os.path.basename(input_filepath)

    cache_mkv_filename: str = input_filename.replace(".", "_") + "_new"
    cache_mkv_filepath: str = ""
    unreliable_meta_data_bool: bool = not reliable_meta_data(
        input_filename=input_filename, media_info_data=media_info_data
    )
    if unreliable_meta_data_bool:
        cache_mkv_filepath = multiplex(
            track_info_list=[
                dict(
                    filepath=input_filepath,
                    sync_delay=0,
                    track_type="video",
                    track_name="",
                    language="",
                    original_index=int(video_info_dict["streamorder"]),
                )
            ],
            output_file_dir=output_file_dir,
            output_file_name=cache_mkv_filename,
        )
        input_filepath = cache_mkv_filepath

    media_info_list: list = MediaInfo.parse(input_filepath).to_data()["tracks"]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )

    video_info_key_set: set = set(video_info_dict.keys())

    play_frame_rate: str = get_proper_frame_rate(
        video_info_dict=video_info_dict,
        video_info_key_set=video_info_key_set,
        
        original_fps=False if unreliable_meta_data_bool else True,
    )
    if not play_frame_rate:
        raise KeyError(
            f"video track of {input_filepath} "
            f"does not have frame_rate info."
        )

    color_range_key: str = "color_range"
    if color_range_key in video_info_key_set:
        color_range: str = video_info_dict[color_range_key].lower()
    else:
        color_range: str = "limited"

    output_filepath: str = os.path.join(output_file_dir, input_filename)

    if os.path.isfile(input_filepath):
        if not os.path.isfile(output_filepath):
            shutil.copyfile(input_filepath, output_filepath)
        elif not os.path.samefile(input_filepath, output_filepath):
            shutil.copyfile(input_filepath, output_filepath)

    video_track_file: VideoTrackFile = VideoTrackFile(
        filepath=output_filepath,
        track_index=get_stream_order(video_info_dict["streamorder"]),
        track_format=video_info_dict["format"].lower(),
        duration_ms=int(float(video_info_dict["duration"])),
        bit_rate_bps=int(video_info_dict["bit_rate"])
        if "bit_rate" in video_info_dict.keys()
        else -1,
        width=video_info_dict["width"],
        height=video_info_dict["height"],
        frame_rate=play_frame_rate,
        frame_count=int(video_info_dict["frame_count"]),
        color_range=color_range,
        color_space=video_info_dict["color_space"]
        if "color_space" in video_info_dict.keys()
        else "",
        chroma_subsampling=video_info_dict["chroma_subsampling"]
        if "chroma_subsampling" in video_info_dict.keys()
        else "",
        bit_depth=int(video_info_dict["bit_depth"])
        if "bit_depth" in video_info_dict.keys()
        else -1,
        delay_ms=int(float(video_info_dict["delay"]))
        if "delay" in video_info_dict.keys()
        else 0,
        stream_size_byte=int(video_info_dict["stream_size"])
        if "stream_size" in video_info_dict.keys()
        else -1,
        title=video_info_dict["title"]
        if "title" in video_info_dict.keys()
        else "",
        language=video_info_dict["language"]
        if "language" in video_info_dict.keys()
        else "",
        default_bool=True
        if "default" not in video_info_dict.keys()
        else (True if video_info_dict["default"].lower() == "yes" else False),
        forced_bool=True
        if "forced" not in video_info_dict.keys()
        else (True if video_info_dict["forced"].lower() == "yes" else False),
    )

    if cache_mkv_filepath:
        delete_info_str: str = f"delete cache mkv {cache_mkv_filepath}"
        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(cache_mkv_filepath)

    return video_track_file


