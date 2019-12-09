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

import re


def get_proper_frame_rate(
    video_info_dict: dict, video_info_key_set: set, original_fps=True
):
    original_frame_rate_key: str = "original_frame_rate"
    original_frame_rate_num_key: str = "framerate_original_num"
    original_frame_rate_den_key: str = "framerate_original_den"
    frame_rate_key: str = "frame_rate"
    frame_rate_num_key: str = "framerate_num"
    frame_rate_den_key: str = "framerate_den"

    original_play_frame_rate = ""
    play_frame_rate = ""
    if original_frame_rate_key in video_info_key_set:
        if (
            original_frame_rate_num_key in video_info_key_set
            and original_frame_rate_den_key in video_info_key_set
        ):
            original_play_frame_rate = (
                f"{video_info_dict[original_frame_rate_num_key]}"
                f"/{video_info_dict[original_frame_rate_den_key]}"
            )
        else:
            original_play_frame_rate = video_info_dict[original_frame_rate_key]
    if frame_rate_key in video_info_key_set:
        if (
            frame_rate_num_key in video_info_key_set
            and frame_rate_den_key in video_info_key_set
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

    return return_fps


def reliable_meta_data(
    input_filename: str, media_info_data: dict, lowest_mkvmerge_version=5
):
    mkv_extension: str = ".mkv"
    m2ts_extension: str = ".m2ts"
    if input_filename.endswith(mkv_extension):
        general_info: dict = media_info_data["tracks"][0]
        writing_application_str: str = general_info["writing_application"]
        mkvmerge_str: str = "mkvmerge"
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
        else:
            return False
    elif input_filename.endswith(m2ts_extension):
        return True
    else:
        return False
