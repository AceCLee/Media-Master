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
import re
import shutil
import subprocess
import sys
from xml.dom import minidom

from pymediainfo import MediaInfo

from ..error import DirNotFoundError, RangeError
from ..track import (
    AudioTrackFile,
    MenuTrackFile,
    TextTrackFile,
    VideoTrackFile,
)
from .chapter import convert_chapter_format, get_chapter_format_info_dict
from .check import check_file_environ_path
from .meta_data import (
    get_float_frame_rate,
    get_proper_frame_rate,
    reliable_meta_data,
    get_proper_color_specification,
    get_proper_hdr_info,
)
from .multiplex import multiplex_mkv

from .timecode import mkv_timecode_2_standard_timecode

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
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str "
            f"instead of {type(output_file_name)}"
        )

    if not isinstance(output_file_suffix, str):
        raise TypeError(
            f"type of output_file_suffix must be str "
            f"instead of {type(output_file_suffix)}"
        )

    if not isinstance(track_type, str):
        raise TypeError(
            f"type of track_type must be str " f"instead of {type(track_type)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
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
                f"{ffmpeg_exe_filename} cannot be found in "
                f"{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in "
                f"environment path"
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

    output_file_fullname: str = (
        f"{output_file_name}_"
        f"{track_type}_index_{stream_identifier}.{track_suffix}"
    )

    output_filepath: str = os.path.join(output_file_dir, output_file_fullname)

    if os.path.isfile(output_filepath):
        skip_info_str: str = (
            f"extraction ffmpeg: {output_filepath} "
            f"already existed, skip extraction."
        )

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

    disable_chapter_copy_param_list = ["-map_chapters", "-1"]

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
    ]

    if track_type == video_type:
        args_list += [no_audio_key, no_subtitle_key, no_data_key]
    elif track_type == audio_type:
        args_list += [no_video_key, no_subtitle_key, no_data_key]
    elif track_type == subtitle_type:
        args_list += [no_video_key, no_audio_key, no_data_key]

    args_list += disable_chapter_copy_param_list

    args_list.append(output_value)

    ffmpeg_param_debug_str: str = (
        f"extraction ffmpeg: param: {subprocess.list2cmdline(args_list)}"
    )
    g_logger.log(logging.DEBUG, ffmpeg_param_debug_str)

    start_info_str: str = (
        f"extraction ffmpeg: starting extracting {output_filepath}"
    )

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)
    
    
    process = subprocess.Popen(args_list)

    process.communicate()

    return_code = process.returncode

    if return_code == 0:
        end_info_str: str = (
            f"extraction ffmpeg: extract {output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"extraction ffmpeg: extract {output_filepath} unsuccessfully."
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
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str "
            f"instead of {type(output_file_name)}"
        )

    if not isinstance(output_file_suffix, str):
        raise TypeError(
            f"type of output_file_suffix must be str "
            f"instead of {type(output_file_suffix)}"
        )

    if not isinstance(track_type, str):
        raise TypeError(
            f"type of track_type must be str instead of {type(track_type)}"
        )

    if not isinstance(track_index, int):
        raise TypeError(
            f"type of track_index must be int "
            f"instead of {type(track_index)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str "
            f"instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkv_suffix_set: set = {".mkv", ".mka", ".mks"}
    _, extension = os.path.splitext(input_filepath)
    if extension not in mkv_suffix_set:
        raise TypeError(
            f"format of input_filepath must be Matroska "
            f"and it has to end with {mkv_suffix_set}"
        )

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"mkvextract dir cannot be found with "
                f"{mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"environment path"
            )

    video_type: str = "video"
    audio_type: str = "audio"
    text_type: str = "text"
    timestamp_type: str = "timecode"
    available_type_set: set = {
        video_type,
        audio_type,
        text_type,
        timestamp_type,
    }
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

    if track_type != timestamp_type:
        index_track_info_dict: dict = next(
            track_info
            for track_info in media_info_list[1:]
            if track_info["streamorder"] == str(track_index)
        )
        index_track_type: str = index_track_info_dict["track_type"].lower()
        if index_track_type != track_type:
            raise ValueError(
                f"stream in {track_index} track is not {track_type} "
                f"but {index_track_type} "
            )
    if not os.path.exists(output_file_dir):
        os.makedirs(output_file_dir)

    track_suffix: str = output_file_suffix.replace(".", "")

    output_file_fullname: str = (
        f"{output_file_name}_index_{track_index}.{track_suffix}"
    )

    output_filepath: str = os.path.join(output_file_dir, output_file_fullname)

    if os.path.isfile(output_filepath):
        skip_info_str: str = (
            f"extraction mkvextract: {output_filepath} "
            f"already existed, skip extraction."
        )

        print(skip_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, skip_info_str)
        return output_filepath

    mkvextract_exe_filepath: str = os.path.join(
        mkvextract_exe_file_dir, mkvextract_exe_filename
    )

    input_value: str = input_filepath

    if track_type in {video_type, audio_type, text_type}:
        track_type_param = "tracks"
    elif track_type in {timestamp_type}:
        track_type_param = "timestamps_v2"
    else:
        raise ValueError

    output_value: str = f"{track_index}:{output_filepath}"

    cmd_param_list: list = [
        mkvextract_exe_filepath,
        input_value,
        track_type_param,
        output_value,
    ]

    mkvextract_param_debug_str: str = (
        f"multiplex mkvextract: param:"
        f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, mkvextract_param_debug_str)

    start_info_str: str = (
        f"multiplex mkvextract: starting extracting {output_filepath}"
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
            f"extraction mkvextract: "
            f"extract {output_filepath} successfully."
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
            "extraction mkvextract: "
            "mkvextract has output at least one warning, "
            "but extraction did continue.\n"
            f"warning:\n{warning_text_str}"
            f"stdout:\n{stdout_text_str}"
        )
        print(warning_str, file=sys.stderr)
        g_logger.log(logging.WARNING, warning_str)
    else:
        error_str = (
            f"extraction mkvextract: "
            f"extract {output_filepath} unsuccessfully."
        )
        print(error_str, file=sys.stderr)
        raise subprocess.CalledProcessError(
            returncode=return_code,
            cmd=subprocess.list2cmdline(cmd_param_list),
            output=stdout_text_str,
        )

    return output_filepath


def extract_mkv_video_timecode(
    filepath: str, output_dir: str, output_name: str
) -> str:
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    timecode_suffix: str = "txt"
    media_info_list: list = MediaInfo.parse(filepath).to_data()["tracks"]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )
    video_sream_order: int = int(video_info_dict["streamorder"])
    output_filepath: str = extract_track_mkvextract(
        input_filepath=filepath,
        output_file_dir=output_dir,
        output_file_name=output_name + "_timecode",
        output_file_suffix=timecode_suffix,
        track_type="timecode",
        track_index=video_sream_order,
    )

    output_filepath = mkv_timecode_2_standard_timecode(output_filepath)

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
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str "
            f"instead of {type(output_file_name)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str "
            f"instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkv_suffix_set: set = {".mkv", ".mka"}

    mkvextract_exe_filename: str = "mkvextract.exe"
    if mkvextract_exe_file_dir:
        if not os.path.isdir(mkvextract_exe_file_dir):
            raise DirNotFoundError(
                f"mkvextract dir cannot be found with "
                f"{mkvextract_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mkvextract_exe_file_dir)
        if mkvextract_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"environment path"
            )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
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
                f"{ffmpeg_exe_filename} cannot be found in "
                f"{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in "
                f"environment path"
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

    text_track_file_list: list = []
    for text_track_index, text_info_dict in enumerate(text_info_list):
        track_index: int = get_stream_order(text_info_dict["streamorder"])

        text_format: str = text_info_dict["format"].lower()
        track_suffix: str = text_format
        if text_format == "pgs":
            track_suffix = "sup"
        elif text_format == "vobsub":
            track_suffix = "idx"
        elif text_format == "utf-8":
            track_suffix = "srt"

        if any(
            input_filepath.endswith(mkv_suffix)
            for mkv_suffix in mkv_suffix_set
        ):
            output_filename: str = (f"{output_file_name}_index_{track_index}")

            output_filepath: str = extract_track_mkvextract(
                input_filepath=input_filepath,
                output_file_dir=output_file_dir,
                output_file_name=output_filename,
                output_file_suffix=track_suffix,
                track_type="text",
                track_index=track_index,
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
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str "
            f"instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    mkv_suffix: str = ".mkv"
    if not input_filepath.endswith(mkv_suffix):
        raise TypeError(
            f"format of input_filepath must be Matroska "
            f"and it has to end with {mkv_suffix}"
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
                f"{mkvextract_exe_filename} cannot be found in "
                f"{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"environment path"
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

    cmd_param_list: list = [
        mkvextract_exe_filepath,
        input_filepath,
        attachment_key,
    ]

    for index, filepath in enumerate(output_attachment_filepath_list):
        cmd_param_list.append(
            attachment_value_template.format(
                attachment_id=index + 1, output_path=filepath
            )
        )

    param_debug_str: str = (
        f"extraction mkvextract attachment: param: "
        f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, param_debug_str)

    start_info_str: str = (
        f"extraction mkvetract attachment: "
        f"start to extract {attachment_filename_list} "
        f"from {input_filepath}"
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
            f"extraction mkvextract attachment: "
            f"extract {attachment_filename_list} "
            f"from {input_filepath} successfully."
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
            "extraction mkvextract attachment: "
            "mkvextract has output at least one warning, "
            "but extraction did continue.\n"
            f"warning:\n{warning_text_str}"
            f"stdout:\n{stdout_text_str}"
        )
        print(warning_str, file=sys.stderr)
        g_logger.log(logging.WARNING, warning_str)
    else:
        error_str = (
            f"extraction mkvextract attachment: "
            f"extract {attachment_filename_list} "
            f"from {input_filepath} unsuccessfully!"
        )
        print(error_str, file=sys.stderr)
        raise subprocess.CalledProcessError(
            returncode=return_code,
            cmd=subprocess.list2cmdline(cmd_param_list),
            output=stdout_text_str,
        )

    return tuple(output_attachment_filepath_list)


def extract_chapter(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    chapter_format="matroska",
    mkvextract_exe_file_dir="",
) -> MenuTrackFile:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str "
            f"instead of {type(output_file_name)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str "
            f"instead of {type(mkvextract_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    all_format_info_dict: dict = get_chapter_format_info_dict()
    if chapter_format not in all_format_info_dict.keys():
        raise RangeError(
            message=(
                f"chapter_format must in {all_format_info_dict.keys()}, "
                f"instead of {chapter_format}"
            ),
            valid_range=str(all_format_info_dict.keys()),
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
                f"{mkvextract_exe_filename} cannot be found in "
                f"{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"environment path"
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

    menu_info_dict: dict = menu_info_list[0]
    time_re_exp: str = "(\\d{2})_(\\d{2})_(\\d{2})(\\d{3})"
    chapter_info_list: list = []
    for key in menu_info_dict.keys():
        re_result = re.search(time_re_exp, key)
        if not re_result:
            continue
        start_time: str = (
            f"{re_result.group(1)}:{re_result.group(2)}:"
            f"{re_result.group(3)}.{re_result.group(4)}"
        )
        chapter_name: str = menu_info_dict[key]
        chapter_info_list.append(
            dict(start_time=start_time, chapter_name=chapter_name)
        )

    if not chapter_info_list:
        return

    matroska_suffix_set: str = {".mkv", ".mka", ".mks"}
    matroska_bool: bool = any(
        input_filepath.endswith(matroska_suffix)
        for matroska_suffix in matroska_suffix_set
    )
    if matroska_bool:
        if chapter_format == "matroska" or chapter_format == "ogm":
            chapter_extension = all_format_info_dict[chapter_format]["ext"]
        else:
            chapter_extension = all_format_info_dict["matroska"]["ext"]

        output_file_fullname: str = output_file_name + chapter_extension
        output_filepath: str = os.path.join(
            output_file_dir, output_file_fullname
        )

        mkvextract_exe_filepath: str = os.path.join(
            mkvextract_exe_file_dir, mkvextract_exe_filename
        )

        menu_key: str = "chapters"
        
        ogm_menu_key: str = "--simple"
        menu_value: str = output_filepath

        cmd_param_list: list = [
            mkvextract_exe_filepath,
            input_filepath,
            menu_key,
            menu_value,
        ]

        if chapter_format == "ogm":
            cmd_param_list.append(ogm_menu_key)

        param_debug_str: str = (
            f"extraction menu: param: "
            f"{subprocess.list2cmdline(cmd_param_list)}"
        )
        g_logger.log(logging.DEBUG, param_debug_str)

        start_info_str: str = (
            f"extraction menu: "
            f"start extract {output_file_fullname} "
            f"from {input_filepath}"
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
                f"extraction mkvextract menu: "
                f"extract {output_file_fullname} "
                f"from {input_filepath} successfully."
            )
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)
        elif return_code == 1:
            warning_prefix = "Warning:"
            warning_text_str = "".join(
                line
                for line in stdout_lines
                if line.startswith(warning_prefix)
            )
            stdout_text_str = "".join(stdout_lines)
            warning_str: str = (
                "extraction mkvextract attachment: "
                "mkvextract has output at least one warning, "
                "but extraction did continue.\n"
                f"warning:\n{warning_text_str}"
                f"stdout:\n{stdout_text_str}"
            )
            print(warning_str, file=sys.stderr)
            g_logger.log(logging.WARNING, warning_str)
        else:
            error_str = (
                f"extraction mkvextract menu: "
                f"extract {output_file_fullname} "
                f"from {input_filepath} unsuccessfully!"
            )
            print(error_str, file=sys.stderr)
            raise subprocess.CalledProcessError(
                returncode=return_code,
                cmd=subprocess.list2cmdline(cmd_param_list),
                output=stdout_text_str,
            )
    else:
        output_file_fullname: str = output_file_name + all_format_info_dict[
            "matroska"
        ]["ext"]
        output_filepath: str = os.path.join(
            output_file_dir, output_file_fullname
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

        with open(output_filepath, "w", encoding="utf-8-sig") as xml_file:
            xml_file.write(chapters_xml.toprettyxml())

    original_chapter_filepath: str = ""
    if matroska_bool:
        if chapter_format != "matroska" and chapter_format != "ogm":
            original_chapter_filepath: str = output_filepath
            output_filepath = convert_chapter_format(
                src_chapter_filepath=output_filepath,
                output_dir=output_file_dir,
                dst_chapter_format=chapter_format,
            )
    else:
        if chapter_format != "matroska":
            original_chapter_filepath: str = output_filepath
            output_filepath = convert_chapter_format(
                src_chapter_filepath=output_filepath,
                output_dir=output_file_dir,
                dst_chapter_format=chapter_format,
            )

    if original_chapter_filepath and os.path.isfile(original_chapter_filepath):
        os.remove(original_chapter_filepath)
        delete_info_str: str = (
            f"extraction menu: delete cache {original_chapter_filepath}"
        )
        g_logger.log(logging.INFO, delete_info_str)
        print(delete_info_str, file=sys.stderr)

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
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str "
            f"instead of {type(output_file_name)}"
        )

    if not isinstance(audio_track, str):
        raise TypeError(
            f"type of audio_track must be str "
            f"instead of {type(audio_track)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str "
            f"instead of {type(mkvextract_exe_file_dir)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
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
                f"{mkvextract_exe_filename} cannot be found in "
                f"{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"environment path"
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
                f"{ffmpeg_exe_filename} cannot be found in "
                f"{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in "
                f"environment path"
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

        mkv_suffix_set: set = {".mkv", ".mka"}
        _, extension = os.path.splitext(input_filepath)
        mkv_bool: bool = extension in mkv_suffix_set

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
            track_suffix = "ec3"
        elif audio_format == "ac-3":
            track_suffix = "ac3"
        elif audio_format == "pcm":
            track_suffix = "wav"
        elif audio_format == "mlp fba":
            track_suffix = "thd"
        
        
        elif audio_format == "wma":
            track_suffix = "wma"
            mkv_bool = False

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
                input_filepath=input_filepath,
                output_file_dir=output_file_dir,
                output_file_name=output_file_name,
                output_file_suffix=track_suffix,
                track_type="audio",
                stream_identifier=int(audio_info_dict["stream_identifier"]),
                ffmpeg_exe_file_dir=ffmpeg_exe_file_dir,
            )

        audio_track_file: AudioTrackFile = AudioTrackFile(
            filepath=output_filepath,
            track_index=0,
            track_format=audio_info_dict["format"].lower(),
            duration_ms=int(float(audio_info_dict["duration"]))
            if "duration" in audio_info_dict.keys()
            else -1,
            bit_rate_bps=-1,
            bit_depth=(
                -1
                if isinstance(audio_info_dict["bit_depth"], str)
                and audio_info_dict["bit_depth"].isdigit()
                else int(audio_info_dict["bit_depth"])
            )
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


def get_video_with_valid_metadata(
    filepath: str, output_dir: str, output_name: str
):
    media_info_data: dict = MediaInfo.parse(filepath).to_data()
    media_info_list: list = media_info_data["tracks"]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )

    full_filename: str = os.path.basename(filepath)
    filename, extension = os.path.splitext(full_filename)

    cache_mkv_filename: str = output_name + "_new"
    cache_mkv_full_filename: str = cache_mkv_filename + ".mkv"
    cache_mkv_filepath: str = os.path.join(output_dir, cache_mkv_full_filename)
    unreliable_meta_data_bool: bool = not reliable_meta_data(
        input_filename=full_filename, media_info_data=media_info_data
    )
    if unreliable_meta_data_bool:
        if not os.path.isfile(cache_mkv_filepath):
            cache_mkv_filepath = multiplex_mkv(
                track_info_list=[
                    dict(
                        filepath=filepath,
                        track_id=int(video_info_dict["streamorder"])
                        if "streamorder" in video_info_dict.keys()
                        and video_info_dict["streamorder"].isdigit()
                        else 0,
                    )
                ],
                output_file_dir=output_dir,
                output_file_name=cache_mkv_filename,
            )
        filepath = cache_mkv_filepath

    return filepath


def get_fr_and_original_fr(video_info_dict: dict):
    frame_rate: str = get_proper_frame_rate(
        video_info_dict=video_info_dict, original_fps=False
    )
    original_frame_rate: str = get_proper_frame_rate(
        video_info_dict=video_info_dict, original_fps=True
    )
    return dict(frame_rate=frame_rate, original_frame_rate=original_frame_rate)


def extract_video_track(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    mkvextract_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> VideoTrackFile:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )

    if not isinstance(output_file_name, str):
        raise TypeError(
            f"type of output_file_name must be str "
            f"instead of {type(output_file_name)}"
        )

    if not isinstance(mkvextract_exe_file_dir, str):
        raise TypeError(
            f"type of mkvextract_exe_file_dir must be str "
            f"instead of {type(mkvextract_exe_file_dir)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
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
                f"{mkvextract_exe_filename} cannot be found in "
                f"{mkvextract_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvextract_exe_filename}):
            raise FileNotFoundError(
                f"{mkvextract_exe_filename} cannot be found in "
                f"environment path"
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
                f"{ffmpeg_exe_filename} cannot be found in "
                f"{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in "
                f"environment path"
            )

    valid_video_filepath: str = get_video_with_valid_metadata(
        filepath=input_filepath,
        output_dir=output_file_dir,
        output_name=output_file_name,
    )

    media_info_list: list = MediaInfo.parse(valid_video_filepath).to_data()[
        "tracks"
    ]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )
    frame_rate_info_dict: dict = get_fr_and_original_fr(video_info_dict)

    color_specification_dict: dict = get_proper_color_specification(
        video_info_dict
    )

    hdr_info_dict: dict = get_proper_hdr_info(video_info_dict)

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
    elif video_format == "mpeg video":
        track_suffix: str = "mpeg"
    else:
        raise RuntimeError(f"unknown video format:{video_format}")

    if mp4_bool:
        track_suffix = mp4_suffix
    elif flv_bool:
        track_suffix = flv_suffix
    elif m4v_bool:
        track_suffix = mp4_suffix

    output_filepath: str = ""
    video_index: int = int(video_info_dict["streamorder"])
    if mkv_bool:
        output_filepath = extract_track_mkvextract(
            input_filepath=input_filepath,
            output_file_dir=output_file_dir,
            output_file_name=output_file_name,
            output_file_suffix=track_suffix,
            track_type="video",
            track_index=video_index,
            mkvextract_exe_file_dir=mkvextract_exe_file_dir,
        )
    else:
        output_filepath = extract_track_ffmpeg(
            input_filepath=input_filepath,
            output_file_dir=output_file_dir,
            output_file_name=output_file_name,
            output_file_suffix=track_suffix,
            track_type="video",
            stream_identifier=video_index,
            ffmpeg_exe_file_dir=ffmpeg_exe_file_dir,
        )

    video_track_file: VideoTrackFile = VideoTrackFile(
        filepath=output_filepath,
        track_index=0,
        track_format=video_info_dict["format"].lower(),
        duration_ms=int(float(video_info_dict["duration"])),
        bit_rate_bps=int(video_info_dict["bit_rate"])
        if "bit_rate" in video_info_dict.keys()
        else -1,
        width=video_info_dict["width"],
        height=video_info_dict["height"],
        frame_rate_mode=video_info_dict["frame_rate_mode"].lower(),
        frame_rate=frame_rate_info_dict["frame_rate"],
        original_frame_rate=frame_rate_info_dict["original_frame_rate"],
        frame_count=int(video_info_dict["frame_count"]),
        color_range=video_info_dict["color_range"].lower()
        if "color_range" in video_info_dict.keys()
        else "limited",
        color_space=video_info_dict["color_space"]
        if "color_space" in video_info_dict.keys()
        else "",
        color_matrix=color_specification_dict["color_matrix"],
        color_primaries=color_specification_dict["color_primaries"],
        transfer=color_specification_dict["transfer"],
        chroma_subsampling=video_info_dict["chroma_subsampling"]
        if "chroma_subsampling" in video_info_dict.keys()
        else "",
        bit_depth=int(video_info_dict["bit_depth"])
        if "bit_depth" in video_info_dict.keys()
        else -1,
        sample_aspect_ratio=video_info_dict["pixel_aspect_ratio"]
        if "pixel_aspect_ratio" in video_info_dict.keys()
        else 1,
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
        hdr_bool=hdr_info_dict != dict(),
        mastering_display_color_primaries=hdr_info_dict[
            "mastering_display_color_primaries"
        ]
        if hdr_info_dict
        else "",
        min_mastering_display_luminance=hdr_info_dict[
            "min_mastering_display_luminance"
        ]
        if hdr_info_dict
        else -1,
        max_mastering_display_luminance=hdr_info_dict[
            "max_mastering_display_luminance"
        ]
        if hdr_info_dict
        else -1,
        max_content_light_level=hdr_info_dict["max_content_light_level"]
        if hdr_info_dict
        else -1,
        max_frameaverage_light_level=hdr_info_dict[
            "max_frameaverage_light_level"
        ]
        if hdr_info_dict
        else -1,
    )

    if valid_video_filepath != input_filepath:
        delete_info_str: str = f"delete cache file {valid_video_filepath}"
        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(valid_video_filepath)

    return video_track_file


def copy_video(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    using_original_if_possible=False,
) -> VideoTrackFile:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str "
            f"instead of {type(input_filepath)}"
        )

    if not isinstance(output_file_dir, str):
        raise TypeError(
            f"type of output_file_dir must be str "
            f"instead of {type(output_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    if not os.path.isdir(output_file_dir):
        os.makedirs(output_file_dir)

    valid_video_filepath: str = get_video_with_valid_metadata(
        filepath=input_filepath,
        output_dir=output_file_dir,
        output_name=output_file_name,
    )

    media_info_list: list = MediaInfo.parse(valid_video_filepath).to_data()[
        "tracks"
    ]
    video_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Video"),
        None,
    )
    frame_rate_info_dict: dict = get_fr_and_original_fr(video_info_dict)

    color_specification_dict: dict = get_proper_color_specification(
        video_info_dict
    )

    hdr_info_dict: dict = get_proper_hdr_info(video_info_dict)

    if valid_video_filepath == input_filepath:
        if using_original_if_possible:
            output_filepath = input_filepath
        else:
            input_full_filename: str = os.path.basename(input_filepath)
            input_extension: str = os.path.splitext(input_full_filename)[1]
            output_full_filename: str = (
                output_file_name + "_copy" + input_extension
            )
            output_filepath: str = os.path.join(
                output_file_dir, output_full_filename
            )
            if not os.path.isfile(output_filepath):
                shutil.copyfile(input_filepath, output_filepath)
    else:
        output_filepath: str = valid_video_filepath

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
        frame_rate_mode=video_info_dict["frame_rate_mode"].lower()
        if "frame_rate_mode" in video_info_dict.keys()
        else "cfr",
        frame_rate=frame_rate_info_dict["frame_rate"],
        original_frame_rate=frame_rate_info_dict["original_frame_rate"],
        frame_count=int(video_info_dict["frame_count"]),
        color_range=video_info_dict["color_range"].lower()
        if "color_range" in video_info_dict.keys()
        else "limited",
        color_space=video_info_dict["color_space"]
        if "color_space" in video_info_dict.keys()
        else "",
        color_matrix=color_specification_dict["color_matrix"],
        color_primaries=color_specification_dict["color_primaries"],
        transfer=color_specification_dict["transfer"],
        chroma_subsampling=video_info_dict["chroma_subsampling"]
        if "chroma_subsampling" in video_info_dict.keys()
        else "",
        bit_depth=int(video_info_dict["bit_depth"])
        if "bit_depth" in video_info_dict.keys()
        else -1,
        sample_aspect_ratio=video_info_dict["pixel_aspect_ratio"]
        if "pixel_aspect_ratio" in video_info_dict.keys()
        else 1,
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
        hdr_bool=hdr_info_dict != dict(),
        mastering_display_color_primaries=hdr_info_dict[
            "mastering_display_color_primaries"
        ]
        if hdr_info_dict
        else "",
        min_mastering_display_luminance=hdr_info_dict[
            "min_mastering_display_luminance"
        ]
        if hdr_info_dict
        else -1,
        max_mastering_display_luminance=hdr_info_dict[
            "max_mastering_display_luminance"
        ]
        if hdr_info_dict
        else -1,
        max_content_light_level=hdr_info_dict["max_content_light_level"]
        if hdr_info_dict
        else -1,
        max_frameaverage_light_level=hdr_info_dict[
            "max_frameaverage_light_level"
        ]
        if hdr_info_dict
        else -1,
    )

    return video_track_file


