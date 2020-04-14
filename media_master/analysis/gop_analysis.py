"""
    gop_analysis.py analyse gop information of video
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
import sys
import subprocess
import logging
import re
import pandas as pd
import numpy as np
from ..util import check_file_environ_path
from ..error import DirNotFoundError
from ..util import save_config

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def video_frame_info(
    input_filepath: str, thread_num=os.cpu_count(), ffprobe_exe_file_dir=""
) -> str:
    if not isinstance(input_filepath, str):
        raise TypeError(
            f"type of input_filepath must be str \
instead of {type(input_filepath)}"
        )

    if not isinstance(thread_num, int):
        raise TypeError(
            f"type of thread_num must be int \
instead of {type(thread_num)}"
        )

    if not isinstance(ffprobe_exe_file_dir, str):
        raise TypeError(
            f"type of ffprobe_exe_file_dir must be str \
instead of {type(ffprobe_exe_file_dir)}"
        )
    if not os.path.isfile(input_filepath):
        raise FileNotFoundError(
            f"input Matroska file cannot be found with {input_filepath}"
        )

    ffprobe_exe_filename: str = "ffprobe.exe"
    if ffprobe_exe_file_dir:
        if not os.path.isdir(ffprobe_exe_file_dir):
            raise DirNotFoundError(
                f"ffprobe dir cannot be found with {ffprobe_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(ffprobe_exe_file_dir)
        if ffprobe_exe_filename not in all_filename_list:
            raise FileNotFoundError(
                f"{ffprobe_exe_filename} cannot be found in \
{ffprobe_exe_file_dir}"
            )
    else:
        if not check_file_environ_path({ffprobe_exe_filename}):
            raise FileNotFoundError(
                f"{ffprobe_exe_filename} cannot be found in \
environment path"
            )

    ffprobe_exe_filepath: str = os.path.join(
        ffprobe_exe_file_dir, ffprobe_exe_filename
    )
    input_file_dir: str = os.path.dirname(input_filepath)
    input_file_basename: str = os.path.basename(input_filepath)
    input_file_suffix: str = f".{input_file_basename.split('.')[-1]}"
    input_file_name: str = input_file_basename.replace(input_file_suffix, "")
    csv_suffix: str = ".csv"
    output_csv_filename: str = f"{input_file_name}{csv_suffix}"
    output_csv_filepath: str = os.path.join(
        input_file_dir, output_csv_filename
    )
    output_filepath: str = output_csv_filepath
    if os.path.isfile(output_filepath):
        skip_info_str: str = f"video_frame_info: {output_filepath} \
already existed, skip analysis."

        print(skip_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, skip_info_str)
        return output_filepath

    thread_key: str = "-threads"
    thread_value: str = str(thread_num)
    select_stream_key: str = "-select_streams"
    map_video_symbol: str = "v"
    map_audio_symbol: str = "a"
    select_stream_value: str = map_video_symbol
    print_format_key: str = "-print_format"
    print_format_value: str = "csv"
    show_entries_key: str = "-show_entries"
    show_entries_value: str = "frame"
    output_symbol: str = ">>"

    args_list: list = [
        ffprobe_exe_filepath,
        thread_key,
        thread_value,
        select_stream_key,
        select_stream_value,
        print_format_key,
        print_format_value,
        show_entries_key,
        show_entries_value,
        input_filepath,
        output_symbol,
        output_filepath,
    ]

    ffmpeg_param_debug_str: str = f"video_frame_info: param:\
{subprocess.list2cmdline(args_list)}"
    print(ffmpeg_param_debug_str, file=sys.stderr)
    g_logger.log(logging.DEBUG, ffmpeg_param_debug_str)

    start_info_str: str = f"video_frame_info: start to analyse \
{input_filepath} to {output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)
    
    
    process = subprocess.Popen(args_list, shell=True)

    return_code = process.wait()

    if return_code == 0:
        end_info_str: str = f"video_frame_info: \
analyse {output_filepath} successfully."
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"video_frame_info: \
analyse {output_filepath} unsuccessfully."
        )

    return output_filepath


def save_high_bitrate_gop_info(
    input_filepath: str,
    config_json_filepath: str,
    thread_num: int,
    config: dict,
    minimum_gop_length=300,
):
    json_dir: str = os.path.dirname(config_json_filepath)
    if not os.path.isdir(json_dir):
        os.makedirs(json_dir)
    csv_filepath: str = video_frame_info(input_filepath, thread_num=thread_num)
    csv_text: str = ""
    with open(csv_filepath, mode="r") as csv_file:
        for line in csv_file.readlines():
            if line.startswith("side_data"):
                continue
            if "N/A" in line:
                continue
            csv_text += line
    csv_text = csv_text.replace("\n\n\n", "\n")
    with open(csv_filepath, mode="w") as csv_file:
        csv_file.write(csv_text)
    unknown_name_list: list = [f"unknown{index}" for index in range(10)]
    original_frame_df: pd.DataFrame = pd.read_csv(
        csv_filepath,
        names=[
            "entry",
            "media_type",
            "data_type",
            "key_frame",
            "pkt_pts",
            "pkt_pts_time",
            "pkt_dts",
            "pkt_dts_time",
            "best_effort_timestamp",
            "best_effort_timestamp_time",
            "pkt_duration",
            "pkt_duration_time",
            "pkt_pos",
            "pkt_size",
            "width",
            "height",
            "pix_fmt",
            "sample_aspect_ratio",
            "pict_type",
            "coded_picture_number",
            "display_picture_number",
            "interlaced_frame",
            "top_field_first",
            "repeat_pict",
            "color_range",
            "color_space1",
            "color_space2",
            "color_space3",
            "unspecified",
        ]
        + unknown_name_list,
        low_memory=False,
    )
    frame_df = original_frame_df[["key_frame", "pkt_size"]]
    ave_size: float = frame_df["pkt_size"].mean()
    frame_df["gop_ave_size"] = np.zeros((frame_df.shape[0], 1))
    frame_df["next_i_frame_index"] = np.zeros(
        (frame_df.shape[0], 1), dtype=int
    )
    key_frame_index_array: np.ndarray = np.array(
        frame_df[frame_df["key_frame"] == 1].index
    )
    key_frame_index_list: list = [key_frame_index_array[0]]

    key_frame_index_array_index: int = 0
    while key_frame_index_array_index < len(key_frame_index_array):
        least_next_key_frame_index: int = key_frame_index_array[
            key_frame_index_array_index
        ] + minimum_gop_length
        next_key_frame_index_index: int = np.searchsorted(
            key_frame_index_array, least_next_key_frame_index
        )
        if next_key_frame_index_index >= len(key_frame_index_array):
            break
        key_frame_index_list.append(
            key_frame_index_array[next_key_frame_index_index]
        )
        key_frame_index_array_index = next_key_frame_index_index
    key_frame_index_array = np.array(key_frame_index_list, dtype=int)

    for gop_index in range(key_frame_index_array.shape[0] - 1):
        index: int = key_frame_index_array[gop_index]
        next_index: int = key_frame_index_array[gop_index + 1]
        mean: float = frame_df["pkt_size"][index:next_index].values.mean()
        frame_df.iloc[index, 2] = mean
        frame_df.iloc[index, 3] = int(next_index)
        

    output_list: list = []
    for key in config["multiple_config"].keys():
        multiple_min: float = -1
        multiple_max: float = -1

        if key.endswith("~"):
            re_exp: str = "([\\d.]+)~"
            re_result = re.search(re_exp, key)
            multiple_min = float(re_result.group(1))
        else:
            re_exp: str = "([\\d.]+)~([\\d.]+)"
            re_result = re.search(re_exp, key)
            multiple_min = float(re_result.group(1))
            multiple_max = float(re_result.group(2))
        
        if multiple_max != -1:
            if multiple_min == 0:
                multiple_min = 0.01
            target_df = frame_df[
                (frame_df["gop_ave_size"] >= multiple_min * ave_size)
                & (frame_df["gop_ave_size"] < multiple_max * ave_size)
            ]
        else:
            target_df = frame_df[
                frame_df["gop_ave_size"] >= multiple_min * ave_size
            ]

        target_list: list = []
        for index, row in target_df.iterrows():
            gop_dict: dict = {}
            gop_dict[config["first_frame_index_key"]] = index
            gop_dict[config["last_frame_index_key"]] = (
                int(row["next_i_frame_index"]) - 1
            )
            target_list.append(gop_dict)

        merge_target_list: list = []
        for index in range(len(target_list)):
            if index == 0:
                merge_target_list.append(target_list[0])
                continue
            if (
                merge_target_list[-1][config["last_frame_index_key"]] + 1
                == target_list[index][config["first_frame_index_key"]]
            ):
                gop_dict: dict = {}
                gop_dict[config["first_frame_index_key"]] = merge_target_list[
                    -1
                ][config["first_frame_index_key"]]
                gop_dict[config["last_frame_index_key"]] = target_list[index][
                    config["last_frame_index_key"]
                ]
                merge_target_list[-1] = gop_dict
            else:
                merge_target_list.append(target_list[index])

        target_dict: dict = {}
        target_dict[
            config["video_transcoding_cmd_param_template_key"]
        ] = config["multiple_config"][key][
            "video_transcoding_cmd_param_template_value"
        ]
        target_dict[config["frame_server_template_filepath_key"]] = config[
            "multiple_config"
        ][key]["frame_server_template_filepath_value"]
        target_dict[config["frame_interval_list_key"]] = merge_target_list
        output_list.append(target_dict)

    save_config(config_json_filepath, dict(gop_info=output_list))
    print(f"save {config_json_filepath}", file=sys.stderr)
    return output_list


def save_series_high_bitrate_gop_info(
    input_video_dir: str,
    input_video_filename_reexp: str,
    output_json_dir: str,
    thread_num: int,
    config: dict,
    minimum_gop_length: int,
):

    if not os.path.isdir(output_json_dir):
        os.makedirs(output_json_dir)

    json_suffix: str = ".json"
    all_gop_info_dict: dict = {}
    for filename in os.listdir(input_video_dir):
        re_result = re.search(
            pattern=input_video_filename_reexp, string=filename
        )
        if re_result:
            input_filepath: str = os.path.join(input_video_dir, filename)
            input_file_basename: str = os.path.basename(input_filepath)
            input_file_suffix: str = f".{input_file_basename.split('.')[-1]}"
            input_file_name: str = input_file_basename.replace(
                input_file_suffix, ""
            )
            json_filename = f"{input_file_name}_gop_info{json_suffix}"
            json_filepath: str = os.path.join(output_json_dir, json_filename)
            print(input_filepath, json_filepath)
            gop_info_list: list = save_high_bitrate_gop_info(
                input_filepath,
                json_filepath,
                thread_num,
                config,
                minimum_gop_length=minimum_gop_length,
            )
            episode_num: int = int(re_result.group(1))
            all_gop_info_dict[str(episode_num)] = gop_info_list
        all_gop_info_json_filename: str = "all_gop_info" + json_suffix
        all_gop_info_json_filepath: str = os.path.join(
            output_json_dir, all_gop_info_json_filename
        )
        save_config(all_gop_info_json_filepath, all_gop_info_dict)


