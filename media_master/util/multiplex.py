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
from .check import check_file_environ_path
from .constant import global_constant
from pymediainfo import MediaInfo
from .string_util import (
    get_unique_printable_filename,
    is_filename_with_valid_mark,
    get_filename_with_valid_mark,
)

import copy

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def remultiplex_ffmpeg(
    input_filepath: str,
    output_file_dir: str,
    output_file_name: str,
    output_file_extension: str,
    add_valid_mark_bool: bool = False,
    ffmpeg_exe_file_dir="",
) -> str:
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

    if not isinstance(output_file_extension, str):
        raise TypeError(
            f"type of output_file_extension must be str "
            f"instead of {type(output_file_extension)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
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
                f"{ffmpeg_exe_filename} cannot be found in " f"{ffmpeg_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffmpeg_exe_filename}):
            raise FileNotFoundError(
                f"{ffmpeg_exe_filename} cannot be found in " f"environment path"
            )
    if not os.path.exists(output_file_dir):
        os.makedirs(output_file_dir)

    ffmpeg_exe_filepath: str = os.path.join(ffmpeg_exe_file_dir, ffmpeg_exe_filename)
    output_filename_fullname: str = output_file_name + output_file_extension
    output_filepath: str = os.path.join(output_file_dir, output_filename_fullname)

    if add_valid_mark_bool:
        valid_output_filename_fullname: str = get_filename_with_valid_mark(
            output_filename_fullname
        )
        valid_output_filepath: str = os.path.join(
            output_file_dir, valid_output_filename_fullname
        )

        if os.path.isfile(output_filepath):
            os.remove(output_filepath)

        if os.path.isfile(valid_output_filepath):
            skip_info_str: str = (
                f"multiplex ffmpeg: {valid_output_filepath} "
                f"already existed, skip multiplexing."
            )

            print(skip_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, skip_info_str)
            return valid_output_filepath

    input_key: str = "-i"
    input_value: str = input_filepath
    overwrite_key: str = "-y"
    codec_key: str = "-codec"
    codec_value: str = "copy"
    output_value: str = output_filepath
    cmd_param_list: list = [
        ffmpeg_exe_filepath,
        input_key,
        input_value,
        overwrite_key,
        codec_key,
        codec_value,
        output_value,
    ]

    ffmpeg_param_debug_str: str = (
        f"multiplex ffmpeg: param:" f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, ffmpeg_param_debug_str)

    start_info_str: str = (f"multiplex ffmpeg: starting multiplexing {output_filepath}")

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process = subprocess.Popen(cmd_param_list)

    process.communicate()

    return_code = process.returncode

    if return_code == 0:
        end_info_str: str = (
            f"multiplex ffmpeg: " f"multiplex {output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        error_str = f"multiplex ffmpeg: " f"multiplex {output_filepath} unsuccessfully."
        print(error_str, file=sys.stderr)
        raise ChildProcessError(error_str)

    if add_valid_mark_bool:
        os.rename(output_filepath, valid_output_filepath)
        output_filepath = valid_output_filepath

    return output_filepath


def multiplex_mkv(
    track_info_list: list,
    output_file_dir: str,
    output_file_name: str,
    file_title="",
    chapters_filepath="",
    attachments_filepath_set=set(),
    add_valid_mark_bool: bool = False,
    mkvmerge_exe_file_dir="",
) -> str:
    if not isinstance(track_info_list, list):
        raise TypeError(
            f"type of track_info_list must be list "
            f"instead of {type(track_info_list)}"
        )

    if track_info_list and not isinstance(track_info_list[0], dict):
        raise TypeError(
            f"type of element of track_info_list must be dict "
            f"instead of {type(track_info_list[0])}"
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

    if not isinstance(chapters_filepath, str):
        raise TypeError(
            f"type of chapters_filepath must be str "
            f"instead of {type(chapters_filepath)}"
        )

    if not isinstance(attachments_filepath_set, set):
        raise TypeError(
            f"type of attachments_filepath_set must be set "
            f"instead of {type(attachments_filepath_set)}"
        )

    if not isinstance(mkvmerge_exe_file_dir, str):
        raise TypeError(
            f"type of mkvmerge_exe_file_dir must be str "
            f"instead of {type(mkvmerge_exe_file_dir)}"
        )

    necessary_key_set: set = {"filepath", "track_id"}

    for infor_dict in track_info_list:
        key_set: set = set(infor_dict.keys())
        for key in necessary_key_set:
            if key not in key_set:
                raise KeyError(f"{infor_dict} misses key {key}")

        filepath: str = infor_dict["filepath"]
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"filepath of {infor_dict} cannot be found with {filepath}"
            )
    if chapters_filepath and not os.path.isfile(chapters_filepath):
        raise FileNotFoundError(f"input chapter file cannot be found with {filepath}")
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
                f"{mkvmerge_exe_filename} cannot be found in "
                f"{mkvmerge_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mkvmerge_exe_filename}):
            raise FileNotFoundError(
                f"{mkvmerge_exe_filename} cannot be found in " "environment path"
            )

    for index, track_info_dict in enumerate(track_info_list):
        if "timecode_filepath" in track_info_dict.keys():
            new_track_info_dict: dict = copy.deepcopy(track_info_dict)
            new_track_info_dict["timestamp_filepath"] = track_info_dict[
                "timecode_filepath"
            ]
            new_track_info_dict.pop("timecode_filepath")
            track_info_list[index] = new_track_info_dict

    selective_key_set: set = {
        "track_type",
        "delay_ms",
        "track_name",
        "language",
        "timestamp_filepath",
    }

    selective_key_default_value_dict: dict = dict(
        delay_ms=0, track_name="", language="", timestamp_filepath=""
    )

    constant = global_constant()

    video_track_type: str = constant.video_type
    audio_track_type: str = constant.audio_type
    subtitle_track_type: str = constant.subtitle_type

    mediainfo_track_type_dict: dict = {
        constant.mediainfo_video_type: constant.video_type,
        constant.mediainfo_audio_type: constant.audio_type,
        constant.mediainfo_subtitle_type: constant.subtitle_type,
    }

    for track_info_dict in track_info_list:
        if track_info_dict["track_id"] == -1:
            continue
        for selective_key in selective_key_set:
            if selective_key in track_info_dict.keys():
                continue
            if selective_key == "track_type":
                media_info_list: list = MediaInfo.parse(
                    track_info_dict["filepath"]
                ).to_data()["tracks"]
                track_mediainfo_dict: dict = next(
                    (
                        track
                        for track in media_info_list
                        if constant.mediainfo_track_id_key in track.keys()
                        and int(track[constant.mediainfo_track_id_key])
                        == track_info_dict["track_id"]
                    ),
                    None,
                )
                track_info_dict["track_type"] = mediainfo_track_type_dict[
                    track_mediainfo_dict["track_type"]
                ]
            else:
                track_info_dict[selective_key] = selective_key_default_value_dict[
                    selective_key
                ]

    available_track_type_set: set = {
        video_track_type,
        audio_track_type,
        subtitle_track_type,
    }

    for infor_dict in track_info_list:
        if track_info_dict["track_id"] == -1:
            continue
        key_set: set = set(infor_dict.keys())
        track_type: str = infor_dict["track_type"]
        if track_type not in available_track_type_set:
            raise RangeError(
                message=(f"value of track_type must in " f"{available_track_type_set}"),
                valid_range=str(available_track_type_set),
            )
    if not os.path.isdir(output_file_dir):
        os.makedirs(output_file_dir)

    mkv_suffix: str = ".mkv"
    mkvmerge_exe_filepath: str = os.path.join(
        mkvmerge_exe_file_dir, mkvmerge_exe_filename
    )
    output_filename_fullname: str = output_file_name + mkv_suffix
    output_filepath: str = os.path.join(output_file_dir, output_filename_fullname)

    if add_valid_mark_bool:
        valid_output_filename_fullname: str = get_filename_with_valid_mark(
            output_filename_fullname
        )
        valid_output_filepath: str = os.path.join(
            output_file_dir, valid_output_filename_fullname
        )

        if os.path.isfile(output_filepath):
            os.remove(output_filepath)

        if os.path.isfile(valid_output_filepath):
            skip_info_str: str = (
                f"multiplex mkvmerge: {valid_output_filepath} "
                f"already existed, skip multiplexing."
            )

            print(skip_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, skip_info_str)
            return valid_output_filepath
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

    timestamp_key: str = "--timestamps"

    mkvmerge_value_format: str = "{track_id}:{value}"

    title_key: str = "--title"
    chapters_key: str = "--chapters"
    attachment_key: str = "--attach-file"
    verbose_key: str = "--verbose"

    def mkvmerge_option_cmd_list(cmd_key: str, value_format: str, track_id: int, value):
        if value:
            cmd_value: str = value_format.format(track_id=track_id, value=value)
            return [cmd_key, cmd_value]
        else:
            return []

    def exclusive_track_type_list(track_type: str):
        all_exclusive_track_type_list: list = [
            no_audio_key,
            no_video_key,
            no_subtitles_key,
            no_attachments_key,
        ]
        return [
            exclusive_track_type
            for exclusive_track_type in all_exclusive_track_type_list
            if track_type not in exclusive_track_type
        ]

    cmd_param_list: list = [
        mkvmerge_exe_filepath,
        verbose_key,
        output_key,
        output_value,
    ]
    for track_info_dict in track_info_list:
        filepath: str = track_info_dict["filepath"]
        track_id: int = int(track_info_dict["track_id"])
        track_cmd_param_list: list = []
        if track_id == -1:
            pass
        elif track_id < 0:
            raise ValueError(
                RangeError(
                    message="track_id must be int in the range of [-1,+inf]",
                    valid_range="[-1,+inf]",
                )
            )
        else:
            track_type: str = track_info_dict["track_type"]
            delay_ms: int = int(track_info_dict["delay_ms"])
            track_name: str = track_info_dict["track_name"]
            language: str = track_info_dict["language"]
            timestamp_filepath: str = track_info_dict["timestamp_filepath"]
            track_key: str = video_track_key if track_type == video_track_type else (
                audio_track_key
                if track_type == audio_track_type
                else subtitle_track_key
            )

            track_cmd_param_list += [track_key, str(track_id)]

            track_cmd_param_list += exclusive_track_type_list(track_type=track_type)

            track_cmd_param_list += mkvmerge_option_cmd_list(
                cmd_key=sync_key,
                value_format=mkvmerge_value_format,
                track_id=track_id,
                value=delay_ms,
            )

            track_cmd_param_list += mkvmerge_option_cmd_list(
                cmd_key=track_name_key,
                value_format=mkvmerge_value_format,
                track_id=track_id,
                value=track_name,
            )

            track_cmd_param_list += mkvmerge_option_cmd_list(
                cmd_key=language_key,
                value_format=mkvmerge_value_format,
                track_id=track_id,
                value=language,
            )

            track_cmd_param_list += mkvmerge_option_cmd_list(
                cmd_key=timestamp_key,
                value_format=mkvmerge_value_format,
                track_id=track_id,
                value=timestamp_filepath,
            )

        track_cmd_param_list.append(filepath)
        cmd_param_list += track_cmd_param_list

    if chapters_filepath:
        cmd_param_list += [chapters_key, chapters_filepath]

    if file_title:
        cmd_param_list += [title_key, file_title]

    if attachments_filepath_set:
        for filepath in attachments_filepath_set:
            cmd_param_list += [attachment_key, filepath]

    mkvmerge_param_debug_str: str = (
        f"multiplex mkvmerge: param: " f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, mkvmerge_param_debug_str)

    start_info_str: str = (f"multiplex mkvmerge: start multiplexing {output_filepath}")

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
            f"multiplex mkvmerge: " f"multiplex {output_filepath} successfully."
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
            f"multiplex mkvmerge: " f"multiplex {output_filepath} unsuccessfully."
        )
        print(error_str, file=sys.stderr)
        raise subprocess.CalledProcessError(
            returncode=return_code,
            cmd=subprocess.list2cmdline(cmd_param_list),
            output=stdout_text_str,
        )

    if add_valid_mark_bool:
        os.rename(output_filepath, valid_output_filepath)
        output_filepath = valid_output_filepath

    return output_filepath


def multiplex_mp4(
    track_info_list: list,
    output_file_dir: str,
    output_file_name: str,
    chapters_filepath="",
    add_valid_mark_bool: bool = False,
    mp4box_exe_file_dir="",
) -> str:
    if not isinstance(track_info_list, list):
        raise TypeError(
            f"type of track_info_list must be list "
            f"instead of {type(track_info_list)}"
        )

    if track_info_list and not isinstance(track_info_list[0], dict):
        raise TypeError(
            f"type of element of track_info_list must be dict "
            f"instead of {type(track_info_list[0])}"
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

    if not isinstance(chapters_filepath, str):
        raise TypeError(
            f"type of chapters_filepath must be str "
            f"instead of {type(chapters_filepath)}"
        )

    if not isinstance(mp4box_exe_file_dir, str):
        raise TypeError(
            f"type of mp4box_exe_file_dir must be str "
            f"instead of {type(mp4box_exe_file_dir)}"
        )

    necessary_key_set: set = {"filepath", "track_id"}

    for infor_dict in track_info_list:
        key_set: set = set(infor_dict.keys())
        for key in necessary_key_set:
            if key not in key_set:
                raise KeyError(f"{infor_dict} misses key {key}")

        filepath: str = infor_dict["filepath"]
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"filepath of {infor_dict} cannot be found with {filepath}"
            )
    if chapters_filepath and not os.path.isfile(chapters_filepath):
        raise FileNotFoundError(f"input chapter file cannot be found with {filepath}")

    mp4box_exe_filename: str = "mp4box.exe"
    if mp4box_exe_file_dir:
        if not os.path.isdir(mp4box_exe_file_dir):
            raise DirNotFoundError(
                f"mp4box dir cannot be found with {mp4box_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(mp4box_exe_file_dir)
        if mp4box_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{mp4box_exe_filename} cannot be found in " f"{mp4box_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({mp4box_exe_filename}):
            raise FileNotFoundError(
                f"{mp4box_exe_filename} cannot be found in " "environment path"
            )

    selective_key_set: set = {"delay_ms", "track_name", "language"}

    selective_key_default_value_dict: dict = dict(
        delay_ms=0, track_name="", language=""
    )

    constant = global_constant()

    video_track_type: str = constant.video_type
    audio_track_type: str = constant.audio_type

    mediainfo_track_type_dict: dict = {
        constant.mediainfo_video_type: constant.video_type,
        constant.mediainfo_audio_type: constant.audio_type,
        constant.mediainfo_subtitle_type: constant.subtitle_type,
    }

    for track_info_dict in track_info_list:
        for selective_key in selective_key_set:
            if selective_key in track_info_dict.keys():
                continue
            if selective_key == "track_type":
                media_info_list: list = MediaInfo.parse(
                    track_info_dict["filepath"]
                ).to_data()["tracks"]
                track_mediainfo_dict: dict = next(
                    (
                        track
                        for track in media_info_list
                        if constant.mediainfo_track_id_key in track.keys()
                        and int(track[constant.mediainfo_track_id_key])
                        == track_info_dict["track_id"]
                    ),
                    None,
                )
                track_info_dict["track_type"] = mediainfo_track_type_dict[
                    track_mediainfo_dict["track_type"]
                ]
            else:
                track_info_dict[selective_key] = selective_key_default_value_dict[
                    selective_key
                ]

    available_track_type_set: set = {video_track_type, audio_track_type}

    for infor_dict in track_info_list:
        if track_info_dict["track_id"] == -1:
            continue
        key_set: set = set(infor_dict.keys())
        track_type: str = infor_dict["track_type"]
        if track_type not in available_track_type_set:
            raise RangeError(
                message=(f"value of track_type must in " f"{available_track_type_set}"),
                valid_range=str(available_track_type_set),
            )
    if not os.path.isdir(output_file_dir):
        os.makedirs(output_file_dir)

    mp4_extension: str = ".mp4"
    mp4box_exe_filepath: str = os.path.join(mp4box_exe_file_dir, mp4box_exe_filename)

    output_filename_fullname: str = output_file_name + mp4_extension
    output_filepath: str = os.path.join(output_file_dir, output_filename_fullname)

    if add_valid_mark_bool:
        valid_output_filename_fullname: str = get_filename_with_valid_mark(
            output_filename_fullname
        )
        valid_output_filepath: str = os.path.join(
            output_file_dir, valid_output_filename_fullname
        )

        if os.path.isfile(output_filepath):
            os.remove(output_filepath)

        if os.path.isfile(valid_output_filepath):
            skip_info_str: str = (
                f"multiplex mp4box: {valid_output_filepath} "
                f"already existed, skip multiplexing."
            )

            print(skip_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, skip_info_str)
            return valid_output_filepath
    force_new_file_key: str = "-new"
    output_value: str = os.path.abspath(output_filepath)
    add_key: str = "-add"
    track_id_option_key: str = "#trackID="
    language_option_key: str = ":lang="
    delay_ms_option_key: str = ":delay="
    track_name_option_key: str = ":name="

    cmd_param_list: list = [
        mp4box_exe_filepath,
        force_new_file_key,
        output_value,
    ]
    for track_info_dict in track_info_list:
        filepath: str = os.path.abspath(track_info_dict["filepath"])
        track_id: int = track_info_dict["track_id"]
        delay_ms: int = track_info_dict["delay_ms"]
        track_name: str = track_info_dict["track_name"]
        language: str = track_info_dict["language"]

        track_info_str: str = filepath

        track_info_str += track_id_option_key + str(track_id)

        if delay_ms:
            track_info_str += delay_ms_option_key + str(delay_ms)
        track_info_str += track_name_option_key + track_name

        if language:
            track_info_str += language_option_key + language

        cmd_param_list += [add_key, track_info_str]

    if chapters_filepath:
        chapters_filepath = os.path.abspath(chapters_filepath)
        cmd_param_list += ["-chap", f"{chapters_filepath}"]

    mp4box_param_debug_str: str = (
        f"multiplex mp4box: param: " f"{subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, mp4box_param_debug_str)
    print(mp4box_param_debug_str, file=sys.stderr)

    start_info_str: str = (f"multiplex mp4box: start multiplexing {output_filepath}")

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process = subprocess.Popen(cmd_param_list)

    process.communicate()

    return_code = process.returncode

    if return_code == 0:
        end_info_str: str = (
            f"multiplex mp4box: multiplex {output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        error_str = f"multiplex mp4box: " f"multiplex {output_filepath} unsuccessfully."
        raise ChildProcessError(error_str)

    if add_valid_mark_bool:
        os.rename(output_filepath, valid_output_filepath)
        output_filepath = valid_output_filepath

    return output_filepath


