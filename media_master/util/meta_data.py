"""
    meta_data.py meta data module of media_master
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
import subprocess
import sys
from fractions import Fraction

from pymediainfo import MediaInfo

from ..error import RangeError
from .constant import global_constant

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def get_proper_sar(sar, max_denominator=100) -> dict:
    re_exp: str = "^(\\d+):(\\d+)$"
    sar_num: int = 0
    sar_den: int = 0

    if isinstance(sar, str):
        if not sar:
            sar_num = 1
            sar_den = 1
        re_result = re.fullmatch(re_exp, sar)
        if re_result:
            sar_num = int(re_result.group(1))
            sar_den = int(re_result.group(2))
        else:
            sar_float: float = float(sar)
    elif isinstance(sar, int) or isinstance(sar, float):
        sar_float: float = float(sar)
    else:
        raise ValueError(f"unknown sar : {sar}")

    if not any([sar_num, sar_den]):
        sar_fraction: Fraction = Fraction(sar_float).limit_denominator(
            max_denominator
        )
        sar_num = sar_fraction.numerator
        sar_den = sar_fraction.denominator

    sar_dict: dict = dict(sar_num=sar_num, sar_den=sar_den)

    return sar_dict


def get_proper_hdr_info(video_info_dict: dict) -> dict:
    constant = global_constant()
    mediainfo_mastering_display_luminance_re_exp: str = (
        constant.mediainfo_mastering_display_luminance_re_exp
    )
    mediainfo_light_level_re_exp: str = constant.mediainfo_light_level_re_exp
    mediainfo_encoder_colorprim_dict: dict = (
        constant.mediainfo_encoder_colorprim_dict
    )
    hdr_info_dict: dict = {}
    if "hdr_format" not in video_info_dict.keys():
        return hdr_info_dict
    hdr_info_dict["mastering_display_color_primaries"] = (
        mediainfo_encoder_colorprim_dict[
            video_info_dict["mastering_display_color_primaries"]
        ]
        if "mastering_display_color_primaries" in video_info_dict.keys()
        else ""
    )

    if "mastering_display_luminance" in video_info_dict.keys():
        re_result = re.search(
            mediainfo_mastering_display_luminance_re_exp,
            video_info_dict["mastering_display_luminance"],
        )
        hdr_info_dict["min_mastering_display_luminance"] = float(
            re_result.groupdict()["min"]
        )
        hdr_info_dict["max_mastering_display_luminance"] = float(
            re_result.groupdict()["max"]
        )
    else:
        hdr_info_dict["min_mastering_display_luminance"] = -1
        hdr_info_dict["max_mastering_display_luminance"] = -1

    if "maximum_content_light_level" in video_info_dict.keys():
        re_result = re.search(
            mediainfo_light_level_re_exp,
            video_info_dict["maximum_content_light_level"],
        )
        hdr_info_dict["max_content_light_level"] = float(
            re_result.groupdict()["num"]
        )
    else:
        hdr_info_dict["max_content_light_level"] = -1

    if "maximum_frameaverage_light_level" in video_info_dict.keys():
        re_result = re.search(
            mediainfo_light_level_re_exp,
            video_info_dict["maximum_frameaverage_light_level"],
        )
        hdr_info_dict["max_frameaverage_light_level"] = float(
            re_result.groupdict()["num"]
        )
    else:
        hdr_info_dict["max_frameaverage_light_level"] = -1

    return hdr_info_dict


def get_colorspace_specification(width: int, height: int, bit_depth: int):
    if not isinstance(width, int):
        raise TypeError(f"type of width must be int instead of {type(width)}")

    if not isinstance(height, int):
        raise TypeError(
            f"type of height must be int instead of {type(height)}"
        )

    if not isinstance(bit_depth, int):
        raise TypeError(
            f"type of bit_depth must be int instead of {type(bit_depth)}"
        )

    if width <= 0:
        raise RangeError(
            message=f"value of width must in [0,inf]", valid_range="[0,inf]"
        )

    if height <= 0:
        raise RangeError(
            message=f"value of height must in [0,inf]", valid_range="[0,inf]"
        )

    if bit_depth <= 0:
        raise RangeError(
            message=f"value of bit_depth must in [0,inf]",
            valid_range="[0,inf]",
        )

    constant = global_constant()

    sd_bool: bool = False
    hd_bool: bool = False
    uhd_bool: bool = False

    if width <= 1024 and height <= 576:
        sd_bool = True
    elif width <= 2048 and height <= 1536:
        hd_bool = True
    else:
        uhd_bool = True

    color_matrix: str = (
        constant.encoder_colormatrix_smpte170
        if sd_bool
        else constant.encoder_colormatrix_bt2020nc
        if uhd_bool
        else constant.encoder_colormatrix_bt709
    )
    color_primaries: str = (
        constant.encoder_colorprim_smpte170
        if sd_bool
        else constant.encoder_colorprim_bt2020
        if uhd_bool
        else constant.encoder_colorprim_bt709
    )

    bt2020_available_bit_depth_tuple: tuple = (
        constant.bt2020_available_bit_depth_tuple
    )

    bt2020_transfer: str = constant.encoder_transfer_smpte2084

    transfer: str = (
        constant.encoder_transfer_smpte170
        if sd_bool
        else bt2020_transfer
        if uhd_bool
        else constant.encoder_transfer_bt709
    )

    colorspace_specification_dict: dict = dict(
        color_matrix=color_matrix,
        color_primaries=color_primaries,
        transfer=transfer,
    )

    return colorspace_specification_dict


def get_proper_color_specification(video_info_dict: dict) -> dict:
    constant = global_constant()
    color_specification_dict: dict = get_colorspace_specification(
        width=video_info_dict[constant.mediainfo_width_key],
        height=video_info_dict[constant.mediainfo_height_key],
        bit_depth=int(video_info_dict[constant.mediainfo_bit_depth_key])
        if constant.mediainfo_bit_depth_key in video_info_dict.keys()
        else 8,
    )

    mediainfo_encoder_colormatrix_dict: dict = (
        constant.mediainfo_encoder_colormatrix_dict
    )

    mediainfo_encoder_colorprim_dict: dict = (
        constant.mediainfo_encoder_colorprim_dict
    )

    mediainfo_encoder_transfer_dict: dict = (
        constant.mediainfo_encoder_transfer_dict
    )

    encoder_colormatrix_transfer_dict: dict = (
        constant.encoder_colormatrix_transfer_dict
    )

    encoder_colormatrix_colorprim_dict: dict = (
        constant.encoder_colormatrix_colorprim_dict
    )

    if constant.mediainfo_colormatrix_key in video_info_dict.keys():
        color_specification_dict[
            "color_matrix"
        ] = mediainfo_encoder_colormatrix_dict[
            video_info_dict[constant.mediainfo_colormatrix_key]
        ]
        if constant.mediainfo_colorprim_key in video_info_dict.keys():
            color_specification_dict[
                "color_primaries"
            ] = mediainfo_encoder_colorprim_dict[
                video_info_dict[constant.mediainfo_colorprim_key]
            ]
        else:
            color_specification_dict[
                "color_primaries"
            ] = encoder_colormatrix_colorprim_dict[
                color_specification_dict["color_matrix"]
            ]
        if constant.mediainfo_transfer_key in video_info_dict.keys():
            color_specification_dict[
                "transfer"
            ] = mediainfo_encoder_transfer_dict[
                video_info_dict[constant.mediainfo_transfer_key]
            ]
        else:
            if (
                color_specification_dict["color_primaries"]
                == constant.vapoursynth_colorprim_bt2020
            ):
                color_specification_dict[
                    "transfer"
                ] = encoder_colormatrix_transfer_dict[
                    color_specification_dict["color_matrix"]
                ]
            else:
                color_specification_dict[
                    "transfer"
                ] = encoder_colormatrix_transfer_dict[
                    color_specification_dict["color_matrix"]
                ]

    return color_specification_dict


def get_float_frame_rate(fps: str) -> float:
    fps = str(fps)
    fps_num: float = 0.0
    if "/" in fps:
        fps_num_list: list = fps.split("/")
        if len(fps_num_list) != 2:
            raise ValueError(f"len(fps_num_list) != 2")
        fps_num = int(fps_num_list[0]) / int(fps_num_list[1])
    elif fps.replace(".", "").isdigit():
        fps_num = float(fps)
    else:
        raise ValueError(f"unknown fps: {fps}")

    return fps_num


def get_proper_frame_rate(video_info_dict: dict, original_fps=False):
    original_frame_rate_key: str = "original_frame_rate"
    original_frame_rate_num_key: str = "framerate_original_num"
    original_frame_rate_den_key: str = "framerate_original_den"
    frame_rate_key: str = "frame_rate"
    frame_rate_num_key: str = "framerate_num"
    frame_rate_den_key: str = "framerate_den"

    original_play_frame_rate = ""
    play_frame_rate = ""
    if original_frame_rate_key in video_info_dict.keys():
        if (
            original_frame_rate_num_key in video_info_dict.keys()
            and original_frame_rate_den_key in video_info_dict.keys()
        ):
            original_play_frame_rate = (
                f"{video_info_dict[original_frame_rate_num_key]}"
                f"/{video_info_dict[original_frame_rate_den_key]}"
            )
        else:
            original_play_frame_rate = video_info_dict[original_frame_rate_key]
    if frame_rate_key in video_info_dict.keys():
        if (
            frame_rate_num_key in video_info_dict.keys()
            and frame_rate_den_key in video_info_dict.keys()
        ):
            play_frame_rate = (
                f"{video_info_dict[frame_rate_num_key]}"
                f"/{video_info_dict[frame_rate_den_key]}"
            )
        else:
            play_frame_rate = video_info_dict[frame_rate_key]

    return_fps = ""

    if original_fps and original_play_frame_rate:
        return_fps = original_play_frame_rate
    elif play_frame_rate:
        return_fps = play_frame_rate

    if return_fps == "23976/1000":
        return_fps = "24000/1001"
    elif return_fps == "29970/1000":
        return_fps = "30000/1001"
    elif return_fps == "59940/1000":
        return_fps = "60000/1001"

    return return_fps


def reliable_meta_data(
    input_filename: str, media_info_data: dict, lowest_mkvmerge_version=10
):
    mp4_extension: str = ".mp4"
    mkv_extension: str = ".mkv"
    vob_extension: str = ".vob"
    m2ts_extension: str = ".m2ts"
    if input_filename.endswith(mkv_extension):
        general_info: dict = media_info_data["tracks"][0]
        writing_application_str: str = general_info["writing_application"]
        mkvmerge_str: str = "mkvmerge"
        voukoder_str: str = "Voukoder"
        mkvmerge_re_exp: str = "mkvmerge v(\\d+)\\.(\\d+)\\.(\\d+)"
        if mkvmerge_str in writing_application_str:
            re_result = re.search(mkvmerge_re_exp, writing_application_str)
            if re_result:
                version = int(re_result.group(1))
                if version < lowest_mkvmerge_version:
                    return False
                else:
                    return True
            else:
                raise RuntimeError(
                    f"Unknown writing_application_str {writing_application_str}"
                )
        elif voukoder_str in writing_application_str:
            return True
        else:
            return False
    elif input_filename.endswith(m2ts_extension):
        return False
    elif input_filename.endswith(mp4_extension):
        return False
    elif input_filename.endswith(vob_extension):
        return False
    else:
        return False


def edit_mkv_prop(
    mkv_filepath: str, info_list: list, mkvpropedit_exe_file_dir=""
):
    if not os.path.isfile(mkv_filepath):
        raise ValueError

    mkvpropedit_exe_filename: str = "mkvpropedit.exe"

    mkvpropedit_exe_filepath: str = os.path.join(
        mkvpropedit_exe_file_dir, mkvpropedit_exe_filename
    )
    edit_key: str = "--edit"
    edit_track_value_format: str = "{selector}:{track_order}"
    set_key: str = "--set"
    set_value_format: str = "{key}={value}"

    cmd_param_list: list = [mkvpropedit_exe_filepath]

    for info_dict in info_list:
        print(info_dict)
        if info_dict["selector"] == "track":
            edit_value: str = edit_track_value_format.format(
                selector=info_dict["selector"],
                track_order=int(info_dict["track_index"]) + 1,
            )
        else:
            raise ValueError
        cmd_param_list.extend(
            [
                edit_key,
                edit_value,
                set_key,
                set_value_format.format(
                    key=info_dict["prop_key"], value=info_dict["prop_value"]
                ),
            ]
        )

    cmd_param_list.append(mkv_filepath)

    mkvpropedit_param_debug_str: str = (
        f"mkvpropedit: param: {subprocess.list2cmdline(cmd_param_list)}"
    )
    g_logger.log(logging.DEBUG, mkvpropedit_param_debug_str)

    start_info_str: str = (
        f"mkvpropedit: start editing prop of {mkv_filepath}"
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
            f"mkvpropedit: edit prop of {mkv_filepath} successfully."
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
            "mkvpropedit: "
            "mkvpropedit has output at least one warning, "
            "but modification did continue.\n"
            f"warning:\n{warning_text_str}"
            f"stdout:\n{stdout_text_str}"
        )
        print(warning_str, file=sys.stderr)
        g_logger.log(logging.WARNING, warning_str)
    else:
        error_str = f"mkvpropedit: edit prop of {mkv_filepath} unsuccessfully."
        print(error_str, file=sys.stderr)
        raise subprocess.CalledProcessError(
            returncode=return_code,
            cmd=subprocess.list2cmdline(cmd_param_list),
            output=stdout_text_str,
        )


def change_mkv_meta_data(mkv_filepath: str, title_map_dict: dict):
    if not os.path.isfile(mkv_filepath):
        raise ValueError

    media_info_list: list = MediaInfo.parse(mkv_filepath).to_data()["tracks"]

    track_info_list: list = [
        track
        for track in media_info_list
        if track["track_type"].lower() != "general"
        and track["track_type"].lower() != "menu"
    ]

    skip_bool: bool = True
    for track_info in track_info_list:
        if (
            "streamorder" in track_info.keys()
            and "title" in track_info.keys()
            and any(
                re.search(re_exp, track_info["title"])
                for re_exp in title_map_dict.keys()
            )
        ):
            skip_bool = False
            break

    if skip_bool:
        return

    mkvpropedit_info_list: list = []
    for track_info in track_info_list:
        if (
            "streamorder" in track_info.keys()
            and "title" in track_info.keys()
            and any(
                re.search(re_exp, track_info["title"])
                for re_exp in title_map_dict.keys()
            )
        ):
            prop_value: str = ""
            for re_exp, value_format in title_map_dict.items():
                re_result = re.search(re_exp, track_info["title"])
                if not re_result:
                    continue
                prop_value = value_format.format(
                    creator=re_result.groupdict()["creator"]
                )
            mkvpropedit_info_list.append(
                dict(
                    selector="track",
                    track_index=int(track_info["streamorder"]),
                    prop_key="name",
                    prop_value=prop_value,
                )
            )

    edit_mkv_prop(mkv_filepath, info_list=mkvpropedit_info_list)


def change_dir_mkv_meta_data(file_dir: str, title_map_dict: dict):
    mkv_extension: str = ".mkv"
    mkv_filename_list: list = [
        filename
        for filename in os.listdir(file_dir)
        if filename.endswith(mkv_extension)
        and os.path.isfile(os.path.join(file_dir, filename))
    ]

    for filename in mkv_filename_list:
        filepath = os.path.join(file_dir, filename)
        print(filepath)
        change_mkv_meta_data(filepath, title_map_dict)


def change_volume_mkv_meta_data(volume: str, title_map_dict: dict):
    for dirpath, dirnames, filenames in os.walk(volume):
        change_dir_mkv_meta_data(dirpath, title_map_dict=title_map_dict)


