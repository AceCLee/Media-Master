"""
    transcode.py transcode video stream
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

import copy
import logging
import os
import re
import subprocess
import sys
import warnings
from collections import deque, namedtuple

from ..error import DirNotFoundError, MissTemplateError, RangeError
from ..util import (
    check_file_environ_path,
    generate_vpy_file,
    get_colorspace_specification,
    get_proper_sar,
    get_reduced_fraction,
    global_constant,
    hash_name,
    is_template,
    load_config,
    replace_config_template_dict,
    replace_param_template_list,
    save_config,
)

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


class VideoTranscoding(object):

    necessary_other_config_key_set: set = {
        "frame_rate",
        "input_full_range_bool",
        "output_full_range_bool",
        "input_video_width",
        "input_video_height",
        "total_frame_cnt",
    }
    mkv_extension: str = ".mkv"
    h265_extension: str = ".265"
    h264_extension: str = ".264"
    stderr_info_max_line_cnt: int = 200

    def __init__(
        self,
        input_video_filepath: str,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
    ):
        if not isinstance(input_video_filepath, str):
            raise TypeError(
                f"type of input_video_filepath must be str "
                f"instead of {type(input_video_filepath)}"
            )
        self._input_video_filepath: str = input_video_filepath

        if not os.path.isfile(input_video_filepath):
            raise FileNotFoundError(
                f"input video file cannot be found with {input_video_filepath}"
            )

        if not isinstance(output_video_dir, str):
            raise TypeError(
                f"type of output_video_dir must be str "
                f"instead of {type(output_video_dir)}"
            )
        self._output_video_dir: str = output_video_dir

        if not isinstance(output_video_filename, str):
            raise TypeError(
                f"type of output_video_filename must be str "
                f"instead of {type(output_video_filename)}"
            )
        self._output_video_filename: str = output_video_filename

        if not isinstance(transcoding_cmd_param_template, list):
            raise TypeError(
                f"type of transcoding_cmd_param_template must be list "
                f"instead of {type(transcoding_cmd_param_template)}"
            )
        self._transcoding_cmd_param_template: list = copy.deepcopy(
            transcoding_cmd_param_template
        )

        if not isinstance(other_config, dict):
            raise TypeError(
                f"type of other_config must be dict "
                f"instead of {type(other_config)}"
            )
        other_config_key_set: set = set(other_config.keys())
        for key in self.necessary_other_config_key_set:
            if key not in other_config_key_set:
                raise KeyError(f"other_config misses key {key}")

        self._other_config: dict = copy.deepcopy(other_config)

        if not os.path.isdir(self._output_video_dir):
            os.makedirs(self._output_video_dir)

        self._input_full_range_bool: bool = self._other_config[
            "input_full_range_bool"
        ]
        self._output_full_range_bool: bool = self._other_config[
            "output_full_range_bool"
        ]

    def color_matrix_cmd_params(
        self, width: int, height: int, output_bit_depth: int
    ) -> list:
        if not isinstance(width, int):
            raise TypeError(
                f"type of width must be int instead of {type(width)}"
            )
        if not isinstance(height, int):
            raise TypeError(
                f"type of height must be int instead of {type(height)}"
            )
        if not isinstance(output_bit_depth, int):
            raise TypeError(
                f"type of output_bit_depth must be int instead of "
                f"{type(output_bit_depth)}"
            )

        if width <= 0:
            raise RangeError(
                message=f"value of width must in (0,inf)",
                valid_range=f"(0,inf)",
            )
        if height <= 0:
            raise RangeError(
                message=f"value of height must in (0,inf)",
                valid_range=f"(0,inf)",
            )

        colorspace_specification_dict: dict = get_colorspace_specification(
            width=width, height=height, bit_depth=output_bit_depth
        )

        colormatrix_param: str = "--colormatrix"
        colormatrix_param_value: str = (
            colorspace_specification_dict["color_matrix"]
        )

        color_primaries_param: str = "--colorprim"
        color_primaries_param_value: str = (
            colorspace_specification_dict["color_primaries"]
        )

        transfer_characteristics_param: str = "--transfer"
        transfer_characteristics_param_value: str = (
            colorspace_specification_dict["transfer"]
        )

        params_list: list = [
            color_primaries_param,
            color_primaries_param_value,
            colormatrix_param,
            colormatrix_param_value,
            transfer_characteristics_param,
            transfer_characteristics_param_value,
        ]

        return params_list

    def _process_color_range_cmd_parmas(
        self,
        transcoding_cmd_param_list: list,
        color_range_param: str,
        full_range_param_value: str,
        limited_range_param_value: str,
    ):
        if color_range_param in set(transcoding_cmd_param_list):
            param_key_index: int = (
                transcoding_cmd_param_list.index(color_range_param)
            )
            param_value = transcoding_cmd_param_list[param_key_index + 1]
            if (
                param_value == full_range_param_value
                and not self._output_full_range_bool
            ) or (
                param_value == limited_range_param_value
                and self._output_full_range_bool
            ):
                warning_str: str = f"whether to output full range yuv is "
                f"different between config output_full_range_bool "
                f"f{self._output_full_range_bool} "
                f"and x265 cmd param {param_value}. "
                f"It may cause inferior output video quality!"
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)
        else:
            param_value = (
                full_range_param_value
                if self._output_full_range_bool
                else limited_range_param_value
            )
            transcoding_cmd_param_list += [color_range_param, param_value]

    def _cal_proper_output_fps(self, original_fps: str, output_fps: str):
        output_fps = int(float(output_fps.replace("fps", "")))
        original_fps_info = get_fpsnum_and_fpsden(original_fps)
        if original_fps_info.fps_den == 1001:
            output_fps_num = output_fps * 1000
            proper_output_fps = f"{output_fps_num}/{original_fps_info.fps_den}"
        elif original_fps_info.fps_den == 1:
            output_fps_num = output_fps
            proper_output_fps = output_fps_num
        else:
            raise ValueError
        return proper_output_fps

    def _get_proper_output_fps(self, original_fps: str, output_fps=""):
        if not output_fps:
            fps = original_fps
        else:
            if output_fps.endswith("fps"):
                fps = str(
                    self._cal_proper_output_fps(
                        original_fps=original_fps, output_fps=output_fps
                    )
                )
            else:
                fps = output_fps

        return fps

    def _process_fps_cmd_param(
        self, transcoding_cmd_param_list: list, other_config: dict
    ):
        frame_rate_mode: str = other_config["frame_rate_mode"]
        frame_rate: str = other_config["frame_rate"]
        original_frame_rate: str = other_config["original_frame_rate"]
        output_fps: str = other_config["output_fps"]
        output_frame_rate_mode: str = other_config["output_frame_rate_mode"]

        if output_frame_rate_mode == "vfr":
            fps = frame_rate
        elif output_frame_rate_mode == "cfr":
            if frame_rate_mode == "vfr":
                fps = self._get_proper_output_fps(
                    original_fps=original_frame_rate, output_fps=output_fps
                )
            elif frame_rate_mode == "cfr":
                fps = self._get_proper_output_fps(
                    original_fps=frame_rate, output_fps=output_fps
                )
            else:
                raise ValueError
        else:
            raise ValueError

        if not isinstance(fps, str):
            raise TypeError(
                f"type of value of fps in "
                f"other_config must be str instead of {type(fps)}"
            )
        fps_key = "--fps"
        transcoding_cmd_param_list += [fps_key, fps]

    def _update_transcoding_cmd_template(self, program_param_dict: dict):
        program_param_dict.update(
            self._other_config["video_transcoding_cmd_param_template_config"]
        )

    def _process_sar_cmd_param(
        self, transcoding_cmd_param_list: list, other_config: dict
    ):
        input_sar_dict: dict = get_proper_sar(other_config["input_sar"])

        sar_value = ""

        output_sar = other_config["output_sar"]
        if output_sar == "" or output_sar == "unchange":
            if (
                input_sar_dict["sar_num"] != 1
                or input_sar_dict["sar_den"] != 1
            ):
                sar_value = (
                    f"{input_sar_dict['sar_num']}:{input_sar_dict['sar_den']}"
                )
        else:
            output_sar_dict: dict = get_proper_sar(output_sar)
            sar_value = (
                f"{output_sar_dict['sar_num']}:{output_sar_dict['sar_den']}"
            )

        if sar_value:
            sar_key = "--sar"
            transcoding_cmd_param_list += [sar_key, sar_value]

        return transcoding_cmd_param_list

    def _process_hdr_cmd_param(
        self, transcoding_cmd_param_list: list, other_config: dict
    ):
        constant = global_constant()
        if other_config["output_dynamic_range_mode"] == "hdr":
            master_display_key: str = "--master-display"
            max_cll_key: str = "--max-cll"
            master_display_value: str = ""
            if (
                other_config["input_mastering_display_color_primaries"]
                == constant.encoder_colorprim_bt2020
            ):
                master_display_value = constant.encoder_master_display_prim_bt2020_format_str.format(
                    max_master_display_luminance=other_config[
                        "input_max_mastering_display_luminance"
                    ]
                    * 1e4,
                    min_master_display_luminance=other_config[
                        "input_min_mastering_display_luminance"
                    ]
                    * 1e4,
                )
            elif (
                other_config["input_mastering_display_color_primaries"]
                == constant.encoder_colorprim_p3
            ):
                master_display_value = constant.encoder_master_display_prim_p3_format_str.format(
                    max_master_display_luminance=other_config[
                        "input_max_mastering_display_luminance"
                    ]
                    * 1e4,
                    min_master_display_luminance=other_config[
                        "input_min_mastering_display_luminance"
                    ]
                    * 1e4,
                )
            else:
                raise ValueError(
                    f"unsupported input_mastering_display_color_primaries: "
                    f"{other_config['input_mastering_display_color_primaries']}"
                )
            transcoding_cmd_param_list += [
                master_display_key,
                master_display_value,
                max_cll_key,
                constant.encoder_max_cll_format_str.format(
                    max_content_light_level=other_config[
                        "input_max_content_light_level"
                    ],
                    max_frameaverage_light_level=other_config[
                        "input_max_frameaverage_light_level"
                    ],
                ),
            ]

        return transcoding_cmd_param_list

    def _cmd_param_list_element_2_str(self, cmd_param_list: list):
        if isinstance(cmd_param_list, list):
            cmd_param_list = [str(element) for element in cmd_param_list]
        return cmd_param_list


class FrameServerVideoTranscoding(VideoTranscoding):

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
    ):
        if not isinstance(frame_server_template_filepath, str):
            raise TypeError(
                f"type of frame_server_template_filepath must be str "
                f"instead of {type(frame_server_template_filepath)}"
            )
        if not os.path.isfile(frame_server_template_filepath):
            raise FileNotFoundError(
                f"input video file cannot be found with "
                f"{frame_server_template_filepath}"
            )
        self._frame_server_template_filepath: str = (
            frame_server_template_filepath
        )

        if not isinstance(frame_server_script_cache_dir, str):
            raise TypeError(
                f"type of frame_server_script_cache_dir must be str "
                f"instead of {type(frame_server_script_cache_dir)}"
            )
        self._frame_server_script_cache_dir: str = (
            frame_server_script_cache_dir
        )

        if not isinstance(frame_server_script_filename, str):
            raise TypeError(
                f"type of frame_server_script_filename must be str "
                f"instead of {type(frame_server_script_filename)}"
            )
        self._frame_server_script_filename: str = frame_server_script_filename

        if not isinstance(frame_server_template_config, dict):
            raise TypeError(
                f"type of frame_server_template_config must be dict "
                f"instead of {type(frame_server_template_config)}"
            )
        self._frame_server_template_config: dict = copy.deepcopy(
            frame_server_template_config
        )

        super(FrameServerVideoTranscoding, self).__init__(
            input_video_filepath,
            output_video_dir,
            output_video_filename,
            transcoding_cmd_param_template,
            other_config,
        )

        if not os.path.isdir(self._frame_server_script_cache_dir):
            os.makedirs(self._frame_server_script_cache_dir)


class NvencVideoTranscoding(VideoTranscoding):

    nvenc_exe_filename = "NVEncC64.exe"

    def __init__(
        self,
        input_video_filepath: str,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        nvenc_exe_dir="",
    ):
        if not isinstance(nvenc_exe_dir, str):
            raise TypeError(
                f"type of nvenc_exe_dir must be str "
                f"instead of {type(nvenc_exe_dir)}"
            )
        if nvenc_exe_dir:
            if not os.path.isdir(nvenc_exe_dir):
                raise DirNotFoundError(
                    f"nvenc dir cannot be found with {nvenc_exe_dir}"
                )
            all_filename_list: list = os.listdir(nvenc_exe_dir)
            if self.nvenc_exe_filename not in all_filename_list:
                raise FileNotFoundError(
                    f"{self.nvenc_exe_filename} cannot be found in "
                    f"{nvenc_exe_dir}"
                )
        else:
            if not check_file_environ_path({self.nvenc_exe_filename}):
                raise FileNotFoundError(
                    f"{self.nvenc_exe_filename} cannot be found in "
                    f"environment path"
                )
        self._nvenc_exe_dir = nvenc_exe_dir

        super(NvencVideoTranscoding, self).__init__(
            input_video_filepath,
            output_video_dir,
            output_video_filename,
            transcoding_cmd_param_template,
            other_config,
        )

    def transcode(self):
        nvenc_cmd_param_list = self._transcoding_cmd_param_template
        program_param_dict: dict = {}

        self._update_transcoding_cmd_template(program_param_dict)

        nvenc_cmd_param_list = replace_param_template_list(
            nvenc_cmd_param_list, program_param_dict
        )

        codec_key_list: list = ["-c", "--codec"]
        codec_value_h264: str = "h264"
        codec_value_h265: str = "hevc"

        codec_exist_bool: bool = False
        codec_key_index: int = -1
        for param in codec_key_list:
            if param in set(nvenc_cmd_param_list):
                codec_exist_bool = True
                codec_key_index = nvenc_cmd_param_list.index(param)
                break

        assert (not codec_exist_bool and codec_key_index == -1) or (
            codec_exist_bool and codec_key_index > -1
        ), (
            "codec_exist_bool and codec_key_index must be "
            "significant simultaneously"
        )

        if codec_exist_bool:
            codec_value: str = nvenc_cmd_param_list[codec_key_index + 1]
            if codec_value == codec_value_h265:
                output_video_suffix: str = self.h265_extension
            elif codec_value == codec_value_h264:
                output_video_suffix: str = self.h264_extension
            else:
                raise RuntimeError("codec must be hevc or h264")
        else:
            output_video_suffix: str = self.h264_extension

        nvenc_exe_filepath: str = os.path.join(
            self._nvenc_exe_dir, self.nvenc_exe_filename
        )
        output_video_fullname: str = (
            self._output_video_filename + output_video_suffix
        )
        output_video_filepath: str = os.path.join(
            self._output_video_dir, output_video_fullname
        )
        program_param_dict: dict = {
            "nvenc_exe_filepath": nvenc_exe_filepath,
            "input_video_filepath": self._input_video_filepath,
            "output_video_filepath": output_video_filepath,
        }

        nvenc_cmd_param_list = replace_param_template_list(
            nvenc_cmd_param_list, program_param_dict
        )
        nvenc_full_range_param: str = "--fullrange"
        if nvenc_full_range_param in set(nvenc_cmd_param_list):
            if not self._output_full_range_bool:
                warnings.warn(
                    (
                        f"whether to output full range yuv is different "
                        f"between config "
                        f"output_full_range_bool "
                        f"{self._output_full_range_bool} and nvenc cmd param "
                        f"{nvenc_full_range_param}"
                    ),
                    RuntimeWarning,
                )
        else:
            if self._output_full_range_bool:
                nvenc_full_range_param.append(nvenc_full_range_param)
        self._process_fps_cmd_param(nvenc_cmd_param_list, self._other_config)
        self._process_sar_cmd_param(nvenc_cmd_param_list, self._other_config)
        self._process_hdr_cmd_param(nvenc_cmd_param_list, self._other_config)

        log_param: str = "--log"
        log_suffix: str = ".log"
        log_file_dir: str = self._output_video_dir
        log_file_fullname: str = self._output_video_filename + log_suffix
        log_filepath: str = os.path.join(log_file_dir, log_file_fullname)
        log_param_value: str = log_filepath
        if log_param not in set(nvenc_cmd_param_list):
            nvenc_cmd_param_list += [log_param, log_param_value]

        if os.path.isfile(log_filepath):
            os.remove(log_filepath)

        nvenc_cmd_param_list = self._cmd_param_list_element_2_str(
            nvenc_cmd_param_list
        )

        nvenc_param_debug_str: str = (
            f"transcode nvenc: param: "
            f"{subprocess.list2cmdline(nvenc_cmd_param_list)}"
        )
        g_logger.log(logging.DEBUG, nvenc_param_debug_str)

        start_info_str: str = (
            f"transcode nvenc: starting transcoding "
            f"{output_video_filepath}"
        )

        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        process = subprocess.Popen(
            nvenc_cmd_param_list,
        )

        process.communicate()

        if process.returncode == 0:
            end_info_str: str = (
                f"transcode nvenc: "
                f"transcoding {output_video_filepath} successfully."
            )
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)
        else:
            transcode_error_str: str = (
                f"transcode nvenc: "
                f"transcoding {output_video_filepath} "
                f"unsuccessfully."
            )
            ChildProcessError(transcode_error_str)

        return output_video_filepath


class VspipeVideoTranscoding(FrameServerVideoTranscoding):
    necessary_vpy_template_key_set: set = {
        "input_filepath",
        "input_full_range_bool",
        "output_full_range_bool",
        "fps_num",
        "fps_den",
        "output_width",
        "output_height",
    }
    available_vpy_template_value_set: set = {
        "{{input_filepath}}",
        "{{input_full_range_bool}}",
        "{{output_full_range_bool}}",
        "{{input_color_matrix}}",
        "{{input_color_primaries}}",
        "{{input_transfer}}",
        "{{fps_num}}",
        "{{fps_den}}",
        "{{output_fps_num}}",
        "{{output_fps_den}}",
        "{{vfr_bool}}",
        "{{input_video_width}}",
        "{{input_video_height}}",
        "{{2x_input_video_width}}",
        "{{2x_input_video_height}}",
        "{{4x_input_video_width}}",
        "{{4x_input_video_height}}",
        "{{first_frame_index}}",
        "{{last_frame_index}}",
        "{{timecode_filepath}}",
    }
    vspipe_exe_filename: str = "vspipe.exe"

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        vspipe_exe_dir="",
    ):
        if not isinstance(vspipe_exe_dir, str):
            raise TypeError(
                f"type of vspipe_exe_dir must be str "
                f"instead of {type(vspipe_exe_dir)}"
            )
        if vspipe_exe_dir:
            if not os.path.isdir(vspipe_exe_dir):
                raise DirNotFoundError(
                    f"vspipe dir cannot be found with {vspipe_exe_dir}"
                )
            all_filename_list: list = os.listdir(vspipe_exe_dir)
            if self.vspipe_exe_filename not in all_filename_list:
                raise FileNotFoundError(
                    f"{self.vspipe_exe_filename} cannot be found in "
                    f"{vspipe_exe_dir}"
                )
        else:
            if not check_file_environ_path({self.vspipe_exe_filename}):
                raise FileNotFoundError(
                    f"{self.vspipe_exe_filename} cannot be found in "
                    f"environment path"
                )
        self._vspipe_exe_dir = vspipe_exe_dir

        super(VspipeVideoTranscoding, self).__init__(
            input_video_filepath,
            frame_server_template_filepath,
            frame_server_script_cache_dir,
            frame_server_script_filename,
            frame_server_template_config,
            output_video_dir,
            output_video_filename,
            transcoding_cmd_param_template,
            other_config,
        )
        for vpy_template in self._frame_server_template_config.values():
            if (
                is_template(str(vpy_template))
                and vpy_template not in self.available_vpy_template_value_set
            ):
                raise RangeError(
                    message=f"unknown vpy template value:{vpy_template}",
                    valid_range=str(self.available_vpy_template_value_set),
                )
        for vpy_template in self.necessary_vpy_template_key_set:
            if vpy_template not in self._frame_server_template_config.keys():
                raise MissTemplateError(
                    message=(
                        f"frame_server_template_config misses "
                        f"template {vpy_template}"
                    ),
                    missing_template=vpy_template,
                )

    def _generate_vpy_script(self, segment_bool=False):
        if self._other_config["output_frame_rate_mode"] == "vfr":
            fps_info = get_fpsnum_and_fpsden(self._other_config["frame_rate"])
            output_fps_info = get_fpsnum_and_fpsden(
                self._other_config["frame_rate"]
            )
        elif self._other_config["output_frame_rate_mode"] == "cfr":
            if self._other_config["frame_rate_mode"] == "vfr":
                fps_info = get_fpsnum_and_fpsden(
                    self._other_config["original_frame_rate"]
                )
                output_fps_info = get_fpsnum_and_fpsden(
                    self._get_proper_output_fps(
                        original_fps=self._other_config["original_frame_rate"],
                        output_fps=self._other_config["output_fps"],
                    )
                )
            elif self._other_config["frame_rate_mode"] == "cfr":
                fps_info = get_fpsnum_and_fpsden(
                    self._other_config["frame_rate"]
                )
                output_fps_info = get_fpsnum_and_fpsden(
                    self._get_proper_output_fps(
                        original_fps=self._other_config["frame_rate"],
                        output_fps=self._other_config["output_fps"],
                    )
                )
            else:
                raise ValueError
        else:
            raise ValueError

        constant = global_constant()

        encoder_fmtconv_colormatrix_dict: dict = constant.encoder_fmtconv_colormatrix_dict
        encoder_fmtconv_colorprim_dict: dict = constant.encoder_fmtconv_colorprim_dict
        encoder_fmtconv_transfer_dict: dict = constant.encoder_fmtconv_transfer_dict

        program_param_dict: dict = {
            "input_filepath": self._input_video_filepath.replace("\\", "/"),
            "input_full_range_bool": self._input_full_range_bool,
            "input_color_matrix": encoder_fmtconv_colormatrix_dict[
                self._other_config["input_color_matrix"]
            ],
            "input_color_primaries": encoder_fmtconv_colorprim_dict[
                self._other_config["input_color_primaries"]
            ],
            "input_transfer": encoder_fmtconv_transfer_dict[
                self._other_config["input_transfer"]
            ],
            "output_full_range_bool": self._output_full_range_bool,
            "fps_num": fps_info.fps_num,
            "fps_den": fps_info.fps_den,
            "output_fps_num": output_fps_info.fps_num,
            "output_fps_den": output_fps_info.fps_den,
            "input_video_width": self._other_config["input_video_width"],
            "2x_input_video_width": 2
            * self._other_config["input_video_width"],
            "4x_input_video_width": 4
            * self._other_config["input_video_width"],
            "input_video_height": self._other_config["input_video_height"],
            "2x_input_video_height": 2
            * self._other_config["input_video_height"],
            "4x_input_video_height": 4
            * self._other_config["input_video_height"],
            "first_frame_index": 0 if segment_bool else -1,
            "last_frame_index": int(self._other_config["total_frame_cnt"])
            if segment_bool
            else -1,
            "vfr_bool": self._other_config["output_frame_rate_mode"] == "vfr",
            "timecode_filepath": self._other_config[
                "video_timecode_filepath"
            ].replace("\\", "/"),
        }

        vpy_template_dict: dict = replace_config_template_dict(
            copy.deepcopy(self._frame_server_template_config),
            copy.deepcopy(program_param_dict),
        )
        self._vpy_template_dict = vpy_template_dict

        self._transcoding_vpy_filepath: str = generate_vpy_file(
            copy.deepcopy(vpy_template_dict),
            self._frame_server_template_filepath,
            self._frame_server_script_cache_dir,
            self._frame_server_script_filename,
        )

        self._vspipe_exe_filepath: str = os.path.join(
            self._vspipe_exe_dir, self.vspipe_exe_filename
        )


class X265VspipeVideoTranscoding(VspipeVideoTranscoding):

    necessary_vspipe_x265_template_set: set = {
        "{{vspipe_exe_filepath}}",
        "{{input_vpy_filepath}}",
        "{{x265_exe_filepath}}",
        "{{output_video_filepath}}",
    }
    x265_exe_filename: str = "x265.exe"

    x265_color_range_param: str = "--range"
    x265_full_range_param_value: str = "full"
    x265_limited_range_param_value: str = "limited"

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        vspipe_exe_dir="",
        x265_exe_dir="",
    ):
        if not isinstance(x265_exe_dir, str):
            raise TypeError(
                f"type of x265_exe_dir must be str "
                f"instead of {type(x265_exe_dir)}"
            )
        if x265_exe_dir:
            if not os.path.isdir(x265_exe_dir):
                raise DirNotFoundError(
                    f"x265 dir cannot be found with {x265_exe_dir}"
                )
            all_filename_list: list = os.listdir(x265_exe_dir)
            if self.x265_exe_filename not in all_filename_list:
                raise FileNotFoundError(
                    f"{self.x265_exe_filename} cannot be found in "
                    f"{x265_exe_dir}"
                )
        else:
            if not check_file_environ_path({self.x265_exe_filename}):
                raise FileNotFoundError(
                    f"{self.x265_exe_filename} cannot be found in "
                    f"environment path"
                )
        self._x265_exe_dir = x265_exe_dir

        super(X265VspipeVideoTranscoding, self).__init__(
            input_video_filepath,
            frame_server_template_filepath,
            frame_server_script_cache_dir,
            frame_server_script_filename,
            frame_server_template_config,
            output_video_dir,
            output_video_filename,
            transcoding_cmd_param_template,
            other_config,
            vspipe_exe_dir,
        )
        for vspipe_x265_template in self.necessary_vspipe_x265_template_set:
            if (
                vspipe_x265_template
                not in self._transcoding_cmd_param_template
            ):
                raise MissTemplateError(
                    message=f"transcoding_cmd_param_template misses \
template {vspipe_x265_template}",
                    missing_template=vspipe_x265_template,
                )

        self._output_file_suffix: str = self.h265_extension

    def transcode(self) -> tuple:
        self._generate_vpy_script()
        x265_exe_filepath: str = os.path.join(
            self._x265_exe_dir, self.x265_exe_filename
        )

        output_video_fullname: str = (
            self._output_video_filename + self._output_file_suffix
        )
        output_video_filepath: str = os.path.join(
            self._output_video_dir, output_video_fullname
        )

        program_param_dict: dict = {
            "vspipe_exe_filepath": self._vspipe_exe_filepath,
            "input_vpy_filepath": self._transcoding_vpy_filepath,
            "x265_exe_filepath": x265_exe_filepath,
            "output_video_filepath": output_video_filepath,
        }

        self._update_transcoding_cmd_template(program_param_dict)

        vspipe_x265_cmd_param_list = replace_param_template_list(
            self._transcoding_cmd_param_template, program_param_dict
        )
        x265_csv_log_level_param: str = "--csv-log-level"
        x265_csv_log_level_param_value: int = 2
        if x265_csv_log_level_param not in set(vspipe_x265_cmd_param_list):
            vspipe_x265_cmd_param_list += [
                x265_csv_log_level_param,
                str(x265_csv_log_level_param_value),
            ]

        x265_csv_log_param: str = "--csv"
        csv_suffix: str = ".csv"
        csv_file_dir: str = self._frame_server_script_cache_dir
        csv_file_fullname: str = self._output_video_filename + csv_suffix
        x265_csv_log_filepath: str = os.path.join(
            csv_file_dir, csv_file_fullname
        )
        x265_csv_log_param_value: str = x265_csv_log_filepath
        if x265_csv_log_param not in set(vspipe_x265_cmd_param_list):
            vspipe_x265_cmd_param_list += [
                x265_csv_log_param,
                x265_csv_log_param_value,
            ]
        self._process_color_range_cmd_parmas(
            transcoding_cmd_param_list=vspipe_x265_cmd_param_list,
            color_range_param=self.x265_color_range_param,
            full_range_param_value=self.x265_full_range_param_value,
            limited_range_param_value=self.x265_limited_range_param_value,
        )
        width: int = self._vpy_template_dict["output_width"]
        height: int = self._vpy_template_dict["output_height"]
        vspipe_x265_cmd_param_list += self.color_matrix_cmd_params(
            width,
            height,
            self._frame_server_template_config["output_bit_depth"],
        )
        self._process_fps_cmd_param(
            vspipe_x265_cmd_param_list, self._other_config
        )
        self._process_sar_cmd_param(
            vspipe_x265_cmd_param_list, self._other_config
        )
        self._process_hdr_cmd_param(
            vspipe_x265_cmd_param_list, self._other_config
        )
        asuna_x265_stylish: str = "--stylish"
        if asuna_x265_stylish in set(vspipe_x265_cmd_param_list):
            vspipe_x265_cmd_param_list.pop(asuna_x265_stylish)
        if os.path.isfile(x265_csv_log_filepath):
            os.remove(x265_csv_log_filepath)

        vspipe_x265_cmd_param_list = self._cmd_param_list_element_2_str(
            vspipe_x265_cmd_param_list
        )

        vspipe_x265_param_debug_str: str = (
            f"transcode x265: param: "
            f"{subprocess.list2cmdline(vspipe_x265_cmd_param_list)}"
        )
        g_logger.log(logging.DEBUG, vspipe_x265_param_debug_str)

        start_info_str: str = (
            f"transcode x265: starting transcoding {output_video_filepath}"
        )

        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        while True:
            process = subprocess.Popen(
                vspipe_x265_cmd_param_list,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                encoding="utf-8",
                errors="ignore",
            )
            x265_infor_re_exp: str = (
                "\\[(\\d+\\.\\d+)%\\] (\\d+)/(\\d+) frames, "
                "(\\d+.\\d+) fps, (\\d+.\\d+) kb/s, "
                "(\\d+.\\d+) (KB|MB|GB), eta "
                "(\\d+:\\d+:\\d+), est.size (\\d+.\\d+) (KB|MB|GB)"
            )
            x265_encode_summary_re_exp: str = (
                "encoded (\\d+) frames in (\\d+.\\d+)s \\((\\d+.\\d+) fps\\), "
                "(\\d+.\\d+) kb/s, Avg QP:(\\d+.\\d+)"
            )

            frame_hint_str: str = "Encoded Frame:"
            percent_hint_str: str = "Percent:"
            fps_hint_str: str = "FPS:"
            bitrate_hint_str: str = "Bitrate:"
            remain_hint_str: str = "Remain:"
            size_hint_str: str = "Size:"
            estimated_size_hint_str: str = "Estimated Size:"

            all_encoded_frame: int = 0
            encode_time_sec: float = 0.0
            encode_fps: float = 0.0
            encode_bitrate: float = 0.0
            ave_qp: float = 0.0
            total_frame_cnt: int = 0

            print("vspipe x265 transcoding ...", end="\n", file=sys.stderr)

            print(
                (
                    f"{frame_hint_str:^19} {percent_hint_str:^10} "
                    f"{fps_hint_str:^12} "
                    f"{bitrate_hint_str:^18} {remain_hint_str:^14} "
                    f"{size_hint_str:^14} "
                    f"{estimated_size_hint_str:^16}"
                ),
                end="\n",
                file=sys.stderr,
            )
            stderr_lines_deque: deque = deque(
                maxlen=self.stderr_info_max_line_cnt
            )
            while process.poll() is None:
                current_line = process.stderr.readline()
                if current_line:
                    stderr_lines_deque.append(current_line)
                re_result = re.search(x265_encode_summary_re_exp, current_line)
                if re_result:
                    all_encoded_frame = int(re_result.group(1))
                    encode_time_sec = float(re_result.group(2))
                    encode_fps = float(re_result.group(3))
                    encode_bitrate = float(re_result.group(4))
                    ave_qp = float(re_result.group(5))
                re_result = re.search(x265_infor_re_exp, current_line)
                if re_result:
                    total_frame_cnt: int = int(re_result.group(3))
                    print(
                        (
                            f"\r{f'{re_result.group(2)}/{re_result.group(3)}':^19} "
                            f"{f'{re_result.group(1)}%':^10} {re_result.group(4):^12} "
                            f"{f'{re_result.group(5)}kbit/s':^18} {re_result.group(8):^14} "
                            f"{f'{re_result.group(6)}{re_result.group(7)}':^14} "
                            f"{f'{re_result.group(9)}{re_result.group(10)}':^16}"
                        ),
                        end="",
                        file=sys.stderr,
                    )

            print("\n", end="", file=sys.stderr)
            if (
                process.returncode == 0
                and all_encoded_frame == total_frame_cnt
                and total_frame_cnt != 0
            ):
                transcode_info_str: str = (
                    f"transcode x265: "
                    f"transcoded {all_encoded_frame} frames in "
                    f"{encode_time_sec} seconds. "
                    f"fps: {encode_fps}, bitrate: {encode_bitrate} kbit/s, "
                    f"average qp: {ave_qp}."
                )
                print(transcode_info_str, file=sys.stderr)
                g_logger.log(logging.DEBUG, transcode_info_str)
                end_info_str: str = (
                    f"transcode x265: "
                    f"transcoding {output_video_filepath} successfully."
                )
                print(end_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, end_info_str)
                break

            if total_frame_cnt == 0:
                warning_str: str = (
                    f"transcode x265:"
                    f"transcoding error, if this waring occurs repeatly "
                    f"please check frameserver script or parameter."
                )
                warnings.warn(warning_str, RuntimeWarning)
                g_logger.log(logging.WARNING, warning_str)

            transcode_detail_info_str: str = (
                f"transcode x265:"
                f"return code: {process.returncode} "
                f"encoded frame cnt: {all_encoded_frame} "
                f"total frame cnt: {total_frame_cnt}"
            )
            g_logger.log(logging.ERROR, transcode_detail_info_str)
            stderr_str: str = "".join(stderr_lines_deque)
            stderr_error_info_str: str = (
                f"transcode x265: " f"stderror:\n{stderr_str}"
            )
            g_logger.log(logging.ERROR, stderr_error_info_str)
            transcode_error_str: str = (
                f"transcode x265: "
                f"transcoding {output_video_filepath} unsuccessfully, "
                f"try again."
            )
            g_logger.log(logging.ERROR, transcode_error_str)

        return (
            output_video_filepath,
            x265_csv_log_filepath,
            encode_fps,
            encode_bitrate,
        )


class GopX265VspipeVideoTranscoding(X265VspipeVideoTranscoding):

    gop_suffix: str = ".gop"
    json_suffix: str = ".json"
    gop_muxer_exe_filename: str = "gop_muxer.exe"
    gop_muxer_output_video_suffix: str = ".mp4"

    segment_identifier_template: str = "{first_frame_index}_{last_frame_index}"

    delete_exclusive_suffix_set: set = {".csv", ".vpy"}

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        gop_frame_cnt: int,
        first_frame_index: int,
        last_frame_index: int,
        vspipe_exe_dir="",
        x265_exe_dir="",
        gop_muxer_exe_dir="",
    ):
        if not isinstance(gop_frame_cnt, int):
            raise TypeError(
                f"type of gop_frame_cnt must be int "
                f"instead of {type(gop_frame_cnt)}"
            )

        if gop_frame_cnt <= 0:
            raise RangeError(
                message=f"value of gop_frame_cnt must in (0,inf)",
                valid_range=f"(0,inf)",
            )
        self._gop_frame_cnt: int = gop_frame_cnt

        if not isinstance(first_frame_index, int):
            raise TypeError(
                f"type of first_frame_index must be int "
                f"instead of {type(first_frame_index)}"
            )

        if first_frame_index < 0:
            raise RangeError(
                message=f"value of first_frame_index must in [0,inf)",
                valid_range=f"[0,inf)",
            )

        if not isinstance(last_frame_index, int):
            raise TypeError(
                f"type of last_frame_index must be int "
                f"instead of {type(last_frame_index)}"
            )

        if last_frame_index < 0:
            raise RangeError(
                message=f"value of last_frame_index must in [0,inf)",
                valid_range=f"[0,inf)",
            )

        if last_frame_index < first_frame_index:
            raise ValueError(
                f"first_frame_index:{first_frame_index} can not be "
                f"greater than last_frame_index:{last_frame_index}"
            )

        self._first_frame_index: int = first_frame_index
        self._last_frame_index: int = last_frame_index

        if not isinstance(gop_muxer_exe_dir, str):
            raise TypeError(
                f"type of gop_muxer_exe_dir must be str "
                f"instead of {type(gop_muxer_exe_dir)}"
            )
        if gop_muxer_exe_dir:
            if not os.path.isdir(gop_muxer_exe_dir):
                raise DirNotFoundError(
                    f"gop_muxer dir cannot be found with {gop_muxer_exe_dir}"
                )
            all_filename_list: list = os.listdir(gop_muxer_exe_dir)
            if self.gop_muxer_exe_filename not in all_filename_list:
                raise FileNotFoundError(
                    f"{self.gop_muxer_exe_filename} cannot be found in "
                    f"{gop_muxer_exe_dir}"
                )
        else:
            if not check_file_environ_path({self.gop_muxer_exe_filename}):
                raise FileNotFoundError(
                    f"{self.gop_muxer_exe_filename} cannot be found in "
                    f"environment path"
                )
        self._gop_muxer_exe_dir = gop_muxer_exe_dir

        super(GopX265VspipeVideoTranscoding, self).__init__(
            input_video_filepath=input_video_filepath,
            frame_server_template_filepath=frame_server_template_filepath,
            frame_server_script_cache_dir=frame_server_script_cache_dir,
            frame_server_script_filename=frame_server_script_filename,
            frame_server_template_config=frame_server_template_config,
            output_video_dir=output_video_dir,
            output_video_filename=output_video_filename,
            transcoding_cmd_param_template=transcoding_cmd_param_template,
            other_config=other_config,
            vspipe_exe_dir=vspipe_exe_dir,
            x265_exe_dir=x265_exe_dir,
        )
        self._orginal_frame_server_script_cache_dir: str = (
            self._frame_server_script_cache_dir
        )
        self._original_frame_server_script_filename: str = (
            self._frame_server_script_filename
        )
        self._original_output_video_dir: str = self._output_video_dir
        self._original_output_video_filename: str = self._output_video_filename
        self._output_file_suffix: str = self.gop_suffix

        self._match_output_fps()

    def _match_output_fps(self):
        if self._other_config["output_frame_rate_mode"] == "cfr":
            if self._other_config["frame_rate_mode"] == "vfr":
                original_fps_info = get_fpsnum_and_fpsden(
                    self._other_config["frame_rate"]
                )
                output_fps_info = get_fpsnum_and_fpsden(
                    self._get_proper_output_fps(
                        original_fps=self._other_config["original_frame_rate"],
                        output_fps=self._other_config["output_fps"],
                    )
                )
            elif self._other_config["frame_rate_mode"] == "cfr":
                original_fps_info = get_fpsnum_and_fpsden(
                    self._other_config["frame_rate"]
                )
                output_fps_info = get_fpsnum_and_fpsden(
                    self._get_proper_output_fps(
                        original_fps=self._other_config["frame_rate"],
                        output_fps=self._other_config["output_fps"],
                    )
                )
            else:
                raise ValueError

            original_fps_float: float = original_fps_info.fps_num / original_fps_info.fps_den
            output_fps_float: float = output_fps_info.fps_num / output_fps_info.fps_den
            self._first_frame_index: int = round(
                self._first_frame_index * output_fps_float / original_fps_float
            )
            self._last_frame_index: int = round(
                self._last_frame_index * output_fps_float / original_fps_float
            )

    def _init_gop_config(self):
        self._gop_cache_filename: str = (
            self._original_output_video_filename
            + f"_{self._first_frame_index}_{self._last_frame_index}"
        )
        self._gop_cache_filename = hash_name(self._gop_cache_filename)
        self._gop_cache_dir: str = os.path.join(
            self._orginal_frame_server_script_cache_dir,
            self._gop_cache_filename,
        )
        if not os.path.isdir(self._gop_cache_dir):
            os.makedirs(self._gop_cache_dir)

    def _init_status_file(self):
        status_json_fullname: str = self._gop_cache_filename + self.json_suffix
        status_json_filepath: str = os.path.join(
            self._gop_cache_dir, status_json_fullname
        )
        if os.path.isfile(status_json_filepath):
            status_dict: dict = load_config(status_json_filepath)
        else:
            status_dict: dict = dict(
                gop_frame_cnt=self._gop_frame_cnt,
                segment_transcode_bool_dict=dict(),
            )
            for frame_index in range(
                self._first_frame_index,
                self._last_frame_index + 1,
                self._gop_frame_cnt,
            ):
                first_frame_index: int = frame_index
                last_frame_index: int = frame_index + self._gop_frame_cnt - 1
                if last_frame_index > self._last_frame_index:
                    last_frame_index = self._last_frame_index
                status_dict["segment_transcode_bool_dict"][
                    self.segment_identifier_template.format(
                        first_frame_index=first_frame_index,
                        last_frame_index=last_frame_index,
                    )
                ] = False
            save_config(status_json_filepath, status_dict)

        self._status_dict: dict = status_dict
        self._status_json_filepath: str = status_json_filepath

    def _transcode_segment(self):
        for frame_index in range(
            self._first_frame_index,
            self._last_frame_index + 1,
            self._gop_frame_cnt,
        ):
            first_frame_index: int = frame_index
            last_frame_index: int = frame_index + self._gop_frame_cnt - 1
            if last_frame_index > self._last_frame_index:
                last_frame_index = self._last_frame_index
            segment_identifier: str = self.segment_identifier_template.format(
                first_frame_index=first_frame_index,
                last_frame_index=last_frame_index,
            )
            if self._status_dict["segment_transcode_bool_dict"][
                segment_identifier
            ]:
                continue
            self._frame_server_template_config[
                "first_frame_index"
            ] = first_frame_index
            self._frame_server_template_config[
                "last_frame_index"
            ] = last_frame_index
            self._frame_server_script_cache_dir = self._gop_cache_dir
            self._output_video_dir = self._gop_cache_dir

            self._output_video_filename = (
                self._original_output_video_filename + "_" + segment_identifier
            )
            print(self._output_video_filename)
            self._output_video_filename = hash_name(
                self._output_video_filename
            )
            self._frame_server_script_filename = self._output_video_filename
            gop_filepath: str = super(
                GopX265VspipeVideoTranscoding, self
            ).transcode()[0]
            self._status_dict["segment_transcode_bool_dict"][
                segment_identifier
            ] = True
            if "gop_filepath_dict" not in self._status_dict.keys():
                self._status_dict["gop_filepath_dict"] = {}
            self._status_dict["gop_filepath_dict"][
                segment_identifier
            ] = gop_filepath
            save_config(self._status_json_filepath, self._status_dict)

        self._all_gop_filepath_list: list = list(
            self._status_dict["gop_filepath_dict"].values()
        )

    def _merge_gop2mp4(self):
        gop_muxer_filepath: str = os.path.join(
            self._gop_muxer_exe_dir, self.gop_muxer_exe_filename
        )
        output_video_filename: str = (
            self._original_output_video_filename + self.gop_suffix
        )
        output_video_filepath: str = os.path.join(
            self._original_output_video_dir, output_video_filename
        )
        real_output_video_filename: str = (
            self._original_output_video_filename
            + self.gop_muxer_output_video_suffix
        )
        real_output_video_filepath: str = os.path.join(
            self._original_output_video_dir, real_output_video_filename
        )
        gop_muxer_cmd_param_list: list = [gop_muxer_filepath]
        gop_muxer_cmd_param_list += self._all_gop_filepath_list
        gop_muxer_cmd_param_list.append(output_video_filepath)

        gop_muxer_cmd_param_list = self._cmd_param_list_element_2_str(
            gop_muxer_cmd_param_list
        )

        gop_muxer_param_debug_str: str = (
            f"transcode x265 gop_muxer: param: "
            f"{subprocess.list2cmdline(gop_muxer_cmd_param_list)}"
        )
        g_logger.log(logging.DEBUG, gop_muxer_param_debug_str)

        start_info_str: str = (
            f"transcode x265 gop_muxer: starting muxing "
            f"{real_output_video_filepath}"
        )

        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        process = subprocess.Popen(gop_muxer_cmd_param_list)

        process.wait()

        if process.returncode == 0:
            end_info_str: str = (
                f"transcode x265 gop_muxer: "
                f"muxing {real_output_video_filepath} successfully."
            )
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)
        else:
            raise RuntimeError(
                f"transcode x265 gop_muxer: "
                f"muxing {real_output_video_filepath} unsuccessfully."
            )

        return real_output_video_filepath

    def _delete_cache_files(self):
        for filename in os.listdir(self._gop_cache_dir):
            exclusive_bool: bool = False
            for suffix in self.delete_exclusive_suffix_set:
                if suffix in filename:
                    exclusive_bool = True
                    break
            if exclusive_bool:
                continue
            filepath: str = os.path.join(self._gop_cache_dir, filename)
            if os.path.isfile(filepath):
                delete_info_str: str = f"transcode x265: delete {filepath}"
                print(delete_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, delete_info_str)
                os.remove(filepath)

    def transcode(self):
        self._init_gop_config()
        self._init_status_file()
        self._transcode_segment()
        output_video_filepath: str = self._merge_gop2mp4()
        self._delete_cache_files()
        return output_video_filepath


class SegmentedConfigX265VspipeTranscoding(GopX265VspipeVideoTranscoding):

    windows_cmd_max_length: int = 8191
    windows_path_max_length: int = 256

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        gop_frame_cnt: int,
        first_frame_index: int,
        last_frame_index: int,
        segmented_transcode_config_list: list,
        vspipe_exe_dir="",
        x265_exe_dir="",
        gop_muxer_exe_dir="",
    ):
        if not isinstance(segmented_transcode_config_list, list):
            raise TypeError(
                f"type of segmented_transcode_config_list must be list "
                f"instead of {type(segmented_transcode_config_list)}"
            )
        for segmented_transcode_config in segmented_transcode_config_list:
            for frame_interval in segmented_transcode_config[
                "frame_interval_list"
            ]:
                segment_first_frame_index: int = frame_interval[
                    "first_frame_index"
                ]
                segment_last_frame_index: int = frame_interval[
                    "last_frame_index"
                ]
                if not isinstance(segment_first_frame_index, int):
                    raise TypeError(
                        f"type of segment_first_frame_index must be int "
                        f"instead of {type(segment_first_frame_index)}"
                    )
                if segment_first_frame_index < 0:
                    raise RangeError(
                        message=(
                            f"value of segment_first_frame_index must "
                            f"in [0,inf)"
                        ),
                        valid_range=f"[0,inf)",
                    )

                if not isinstance(segment_last_frame_index, int):
                    raise TypeError(
                        f"type of segment_last_frame_index must be int "
                        f"instead of {type(segment_last_frame_index)}"
                    )
                if segment_last_frame_index < 0:
                    raise RangeError(
                        message=(
                            f"value of segment_last_frame_index must "
                            f"in [0,inf)"
                        ),
                        valid_range=f"[0,inf)",
                    )

                if segment_last_frame_index < segment_first_frame_index:
                    raise ValueError(
                        f"segment_first_frame_index:{segment_first_frame_index} can not be "
                        f"greater than segment_last_frame_index:{segment_last_frame_index}"
                    )
                if segment_last_frame_index > last_frame_index:
                    raise ValueError(
                        f"segment_last_frame_index:{segment_last_frame_index} can not be "
                        f"greater than last_frame_index:{last_frame_index}"
                    )
                if segment_first_frame_index < first_frame_index:
                    raise ValueError(
                        f"first_frame_index:{first_frame_index} can not be "
                        f"greater than segment_first_frame_index:{segment_first_frame_index}"
                    )
        self._segmented_transcode_config_list: list = segmented_transcode_config_list
        super(SegmentedConfigX265VspipeTranscoding, self).__init__(
            input_video_filepath=input_video_filepath,
            frame_server_template_filepath=frame_server_template_filepath,
            frame_server_script_cache_dir=frame_server_script_cache_dir,
            frame_server_script_filename=frame_server_script_filename,
            frame_server_template_config=frame_server_template_config,
            output_video_dir=output_video_dir,
            output_video_filename=output_video_filename,
            transcoding_cmd_param_template=transcoding_cmd_param_template,
            other_config=other_config,
            gop_frame_cnt=gop_frame_cnt,
            first_frame_index=first_frame_index,
            last_frame_index=last_frame_index,
            vspipe_exe_dir=vspipe_exe_dir,
            x265_exe_dir=x265_exe_dir,
        )

    def _init_segment_config_list(self):
        general_segmented_transcode_config_list: list = []
        for config in self._segmented_transcode_config_list:
            for frame_interval_dict in config["frame_interval_list"]:
                general_segmented_transcode_config_list.append(
                    dict(
                        video_transcoding_cmd_param_template=config[
                            "video_transcoding_cmd_param_template"
                        ],
                        frame_server_template_filepath=config[
                            "frame_server_template_filepath"
                        ],
                        frame_interval_dict=dict(
                            first_frame_index=frame_interval_dict[
                                "first_frame_index"
                            ],
                            last_frame_index=frame_interval_dict[
                                "last_frame_index"
                            ],
                        ),
                    )
                )
        general_segmented_transcode_config_list.sort(
            key=lambda element: element["frame_interval_dict"][
                "first_frame_index"
            ]
        )

        if general_segmented_transcode_config_list:
            unspecified_segmented_transcode_config_list: list = []
            if (
                general_segmented_transcode_config_list[0][
                    "frame_interval_dict"
                ]["first_frame_index"]
                > self._first_frame_index
            ):
                unspecified_segmented_transcode_config_list.append(
                    dict(
                        video_transcoding_cmd_param_template=(
                            self._transcoding_cmd_param_template
                        ),
                        frame_server_template_filepath=(
                            self._frame_server_template_filepath
                        ),
                        frame_interval_dict=dict(
                            first_frame_index=self._first_frame_index,
                            last_frame_index=(
                                general_segmented_transcode_config_list[0][
                                    "frame_interval_dict"
                                ]["first_frame_index"]
                                - 1
                            ),
                        ),
                    )
                )

            last_last_frame_index: int = -1
            for config in general_segmented_transcode_config_list:
                segment_first_frame_index: int = config["frame_interval_dict"][
                    "first_frame_index"
                ]
                segment_last_frame_index: int = config["frame_interval_dict"][
                    "last_frame_index"
                ]
                if last_last_frame_index == -1:
                    last_last_frame_index = segment_last_frame_index
                    continue
                if last_last_frame_index + 1 == segment_first_frame_index:
                    last_last_frame_index = segment_last_frame_index
                    continue
                unspecified_segmented_transcode_config_list.append(
                    dict(
                        video_transcoding_cmd_param_template=(
                            self._transcoding_cmd_param_template
                        ),
                        frame_server_template_filepath=(
                            self._frame_server_template_filepath
                        ),
                        frame_interval_dict=dict(
                            first_frame_index=last_last_frame_index + 1,
                            last_frame_index=segment_first_frame_index - 1,
                        ),
                    )
                )
                last_last_frame_index = segment_last_frame_index

            if last_last_frame_index < self._last_frame_index:
                unspecified_segmented_transcode_config_list.append(
                    dict(
                        video_transcoding_cmd_param_template=(
                            self._transcoding_cmd_param_template
                        ),
                        frame_server_template_filepath=(
                            self._frame_server_template_filepath
                        ),
                        frame_interval_dict=dict(
                            first_frame_index=last_last_frame_index + 1,
                            last_frame_index=self._last_frame_index,
                        ),
                    )
                )

            general_segmented_transcode_config_list += (
                unspecified_segmented_transcode_config_list
            )

        else:
            general_segmented_transcode_config_list: list = [
                dict(
                    video_transcoding_cmd_param_template=(
                        self._transcoding_cmd_param_template
                    ),
                    frame_server_template_filepath=(
                        self._frame_server_template_filepath
                    ),
                    frame_interval_dict=dict(
                        first_frame_index=self._first_frame_index,
                        last_frame_index=self._last_frame_index,
                    ),
                )
            ]

        general_segmented_transcode_config_list.sort(
            key=lambda element: element["frame_interval_dict"][
                "first_frame_index"
            ]
        )

        for element in general_segmented_transcode_config_list:
            print(element["frame_interval_dict"], file=sys.stderr)
            print(element["frame_server_template_filepath"], file=sys.stderr)
            print(
                element["video_transcoding_cmd_param_template"],
                file=sys.stderr,
            )
            print("", file=sys.stderr)

        hash_str_length: int = 6
        assumptive_path_length: int = len(
            self._frame_server_script_cache_dir
        ) + hash_str_length * 2 + len(os.sep) * 2 + len(
            "-000000.hevc-gop-data"
        )
        print(
            f"assumptive_path_length: {assumptive_path_length}",
            file=sys.stderr,
        )
        if assumptive_path_length > self.windows_path_max_length:
            raise RuntimeError(
                "Cache dir length is too long to save gop data. "
                "Please decrease cache dir length!"
            )
        assumptive_cmd_length: int = len(
            general_segmented_transcode_config_list
        ) * (
            len(self._frame_server_script_cache_dir)
            + hash_str_length * 2
            + len(os.sep) * 2
            + len(self.gop_suffix)
            + len(" ")
        ) + len(
            self.gop_muxer_exe_filename
        ) + self.windows_path_max_length + len(
            " "
        ) * 2
        print(
            f"assumptive_cmd_length: {assumptive_cmd_length}", file=sys.stderr
        )
        if assumptive_cmd_length > self.windows_cmd_max_length:
            raise RuntimeError(
                "Gop count is too many to pass parameter to windows CMD. "
                "and "
                "Cache dir length is too long to save gop data. "
                "Please reduce gop count!"
                "or "
                "Please decrease cache dir length!"
            )

        self._general_segmented_transcode_config_list = (
            general_segmented_transcode_config_list
        )

    def _transcode_configured_segment(self):
        all_gop_filepath_list: list = []
        self._gop_cache_dir_set: set = set()
        for config in self._general_segmented_transcode_config_list:
            self._first_frame_index = config["frame_interval_dict"][
                "first_frame_index"
            ]
            self._last_frame_index = config["frame_interval_dict"][
                "last_frame_index"
            ]
            self._match_output_fps()
            self._transcoding_cmd_param_template = config[
                "video_transcoding_cmd_param_template"
            ]
            self._frame_server_template_filepath = config[
                "frame_server_template_filepath"
            ]
            self._init_gop_config()
            self._gop_cache_dir_set.add(self._gop_cache_dir)
            self._init_status_file()
            self._transcode_segment()
            all_gop_filepath_list += list(
                self._status_dict["gop_filepath_dict"].values()
            )
        self._all_gop_filepath_list = all_gop_filepath_list
        print(self._all_gop_filepath_list)

    def _delete_cache_files(self):
        for gop_cache_dir in self._gop_cache_dir_set:
            for filename in os.listdir(gop_cache_dir):
                exclusive_bool: bool = False
                for suffix in self.delete_exclusive_suffix_set:
                    if suffix in filename:
                        exclusive_bool = True
                        break
                if exclusive_bool:
                    continue
                filepath: str = os.path.join(gop_cache_dir, filename)
                if os.path.isfile(filepath):
                    delete_info_str: str = f"transcode x265: delete {filepath}"
                    print(delete_info_str, file=sys.stderr)
                    g_logger.log(logging.INFO, delete_info_str)
                    os.remove(filepath)

    def transcode(self):
        self._init_segment_config_list()
        self._transcode_configured_segment()
        output_video_filepath: str = self._merge_gop2mp4()
        self._delete_cache_files()
        return output_video_filepath


class X264VspipeVideoTranscoding(VspipeVideoTranscoding):

    necessary_vspipe_x264_template_set: set = {
        "{{vspipe_exe_filepath}}",
        "{{input_vpy_filepath}}",
        "{{x264_exe_filepath}}",
        "{{output_video_filepath}}",
    }
    x264_exe_filename: str = "x264.exe"

    x264_color_range_param: str = "--range"
    x264_full_range_param_value: str = "pc"
    x264_limited_range_param_value: str = "tv"

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        vspipe_exe_dir="",
        x264_exe_dir="",
    ):
        if not isinstance(x264_exe_dir, str):
            raise TypeError(
                f"type of x264_exe_dir must be str "
                f"instead of {type(x264_exe_dir)}"
            )
        if x264_exe_dir:
            if not os.path.isdir(x264_exe_dir):
                raise DirNotFoundError(
                    f"x264 dir cannot be found with {x264_exe_dir}"
                )
            all_filename_list: list = os.listdir(x264_exe_dir)
            if self.x264_exe_filename not in all_filename_list:
                raise FileNotFoundError(
                    f"{self.x264_exe_filename} cannot be found in "
                    f"{x264_exe_dir}"
                )
        else:
            if not check_file_environ_path({self.x264_exe_filename}):
                raise FileNotFoundError(
                    f"{self.x264_exe_filename} cannot be found in "
                    f"environment path"
                )
        self._x264_exe_dir = x264_exe_dir

        super(X264VspipeVideoTranscoding, self).__init__(
            input_video_filepath,
            frame_server_template_filepath,
            frame_server_script_cache_dir,
            frame_server_script_filename,
            frame_server_template_config,
            output_video_dir,
            output_video_filename,
            transcoding_cmd_param_template,
            other_config,
            vspipe_exe_dir,
        )
        for vspipe_x264_template in self.necessary_vspipe_x264_template_set:
            if (
                vspipe_x264_template
                not in self._transcoding_cmd_param_template
            ):
                raise MissTemplateError(
                    message=(
                        f"transcoding_cmd_param_template misses "
                        f"template {vspipe_x264_template}"
                    ),
                    missing_template=vspipe_x264_template,
                )

        self._delete_cache_files()

    def _delete_cache_files(self):
        constant = global_constant()
        lwi_extension: str = (
            constant.vapoursynth_lwlibavsource_cache_file_extension
        )
        lwi_filepath: str = self._input_video_filepath + lwi_extension
        if os.path.isfile(lwi_filepath):
            os.remove(lwi_filepath)

    def transcode(self):
        self._generate_vpy_script()
        x264_exe_filepath: str = os.path.join(
            self._x264_exe_dir,
            self.x264_exe_filename
        )

        output_video_fullname: str = (
            self._output_video_filename + self.h264_extension
        )
        output_video_filepath: str = os.path.join(
            self._output_video_dir, output_video_fullname
        )

        program_param_dict: dict = {
            "vspipe_exe_filepath": self._vspipe_exe_filepath,
            "input_vpy_filepath": self._transcoding_vpy_filepath,
            "x264_exe_filepath": x264_exe_filepath,
            "output_video_filepath": output_video_filepath,
            "cache_dir": self._frame_server_script_cache_dir,
        }

        self._update_transcoding_cmd_template(program_param_dict)

        vspipe_x264_cmd_param_list = replace_param_template_list(
            self._transcoding_cmd_param_template, program_param_dict
        )
        vspipe_progress_param_list: list = ["--progress", "-p"]
        exist_bool: bool = any(
            param in vspipe_progress_param_list
            for param in vspipe_x264_cmd_param_list
        )
        if not exist_bool:
            first_param = vspipe_x264_cmd_param_list[0]
            other_param_list = vspipe_x264_cmd_param_list[1:]
            vspipe_x264_cmd_param_list = [
                first_param,
                vspipe_progress_param_list[0],
            ] + other_param_list
        self._process_color_range_cmd_parmas(
            transcoding_cmd_param_list=vspipe_x264_cmd_param_list,
            color_range_param=self.x264_color_range_param,
            full_range_param_value=self.x264_full_range_param_value,
            limited_range_param_value=self.x264_limited_range_param_value,
        )
        width: int = self._vpy_template_dict["output_width"]
        height: int = self._vpy_template_dict["output_height"]
        vspipe_x264_cmd_param_list += self.color_matrix_cmd_params(
            width,
            height,
            self._frame_server_template_config["output_bit_depth"],
        )
        self._process_fps_cmd_param(
            vspipe_x264_cmd_param_list, self._other_config
        )
        self._process_sar_cmd_param(
            vspipe_x264_cmd_param_list, self._other_config
        )
        x264_log_level_param: str = "--log-file-level"
        x264_log_level_param_value: str = "debug"
        if x264_log_level_param not in set(vspipe_x264_cmd_param_list):
            vspipe_x264_cmd_param_list += [
                x264_log_level_param,
                str(x264_log_level_param_value),
            ]

        x264_log_param: str = "--log-file"
        log_suffix: str = ".log"
        log_file_dir: str = self._frame_server_script_cache_dir
        log_file_fullname: str = self._output_video_filename + log_suffix
        x264_log_filepath: str = os.path.join(log_file_dir, log_file_fullname)
        x264_log_param_value: str = x264_log_filepath
        if x264_log_param not in set(vspipe_x264_cmd_param_list):
            vspipe_x264_cmd_param_list += [
                x264_log_param,
                x264_log_param_value,
            ]
        if os.path.isfile(x264_log_filepath):
            os.remove(x264_log_filepath)

        if os.path.isfile(output_video_filepath):
            os.remove(output_video_filepath)

        vspipe_x264_cmd_param_list = self._cmd_param_list_element_2_str(
            vspipe_x264_cmd_param_list
        )

        vspipe_x264_param_debug_str: str = (
            f"transcode x264: param: "
            f"{subprocess.list2cmdline(vspipe_x264_cmd_param_list)}"
        )
        g_logger.log(logging.DEBUG, vspipe_x264_param_debug_str)

        start_info_str: str = (
            f"transcode x264: starting transcoding {output_video_filepath}"
        )

        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        while True:
            process = subprocess.Popen(
                vspipe_x264_cmd_param_list,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                encoding="utf-8",
                errors="ignore",
            )
            vspipe_infor_re_exp: str = r"Frame: (\d+)/(\d+)"
            x264_infor_re_exp: str = (
                "(\\d+) frames: (\\d+.\\d+) fps, (\\d+.\\d+) kb/s"
            )
            x264_encode_summary_re_exp: str = (
                "encoded (\\d+) frames, (\\d+\\.\\d+) fps, (\\d+\\.\\d+) kb/s"
            )

            total_frame_cnt: int = -1
            x264_encoded_frame: int = -1
            vspipe_processed_frame: int = -1
            ave_fps: float = 0.0
            ave_bitrate: float = 0.0

            frame_hint_str: str = "Encoded Frame:"
            percent_hint_str: str = "Percent:"
            fps_hint_str: str = "FPS:"
            bitrate_hint_str: str = "Bitrate:"
            remain_hint_str: str = "Remain:"

            all_encoded_frame: int = 0
            encode_fps: float = 0.0
            encode_bitrate: float = 0.0

            print("vspipe x264 transcoding ...", end="\n", file=sys.stderr)

            print(
                (
                    f"{frame_hint_str:^19} {percent_hint_str:^10} "
                    f"{fps_hint_str:^12} "
                    f"{bitrate_hint_str:^18} {remain_hint_str:^14}"
                ),
                end="\n",
                file=sys.stderr,
            )
            stderr_lines_deque: deque = deque(
                maxlen=self.stderr_info_max_line_cnt
            )
            while process.poll() is None:
                current_line = process.stderr.readline()
                if current_line:
                    stderr_lines_deque.append(current_line)
                re_result = re.search(vspipe_infor_re_exp, current_line)
                if re_result:
                    vspipe_processed_frame = int(re_result.group(1))
                    total_frame_cnt = int(re_result.group(2))

                re_result = re.search(x264_infor_re_exp, current_line)
                if re_result:
                    x264_encoded_frame = int(re_result.group(1))

                    ave_fps = float(re_result.group(2))
                    ave_bitrate = float(re_result.group(3))

                re_result = re.search(x264_encode_summary_re_exp, current_line)
                if re_result:
                    all_encoded_frame = int(re_result.group(1))
                    encode_fps = float(re_result.group(2))
                    encode_bitrate = float(re_result.group(3))
                if total_frame_cnt != -1:
                    if x264_encoded_frame != -1:
                        remain_frame_cnt: int = (
                            total_frame_cnt - x264_encoded_frame
                        )
                        remain_second: float = remain_frame_cnt / ave_fps
                        remain_minute: float = remain_second / 60
                        percent: float = (
                            x264_encoded_frame / total_frame_cnt * 100
                        )
                        display_percent_str: str = f"{percent:.2f}%"
                        display_bitrate_str: str = f"{ave_bitrate:.2f}kbit/s"
                        display_remain_str: str = f"{remain_minute:.2f}min"
                        print(
                            (
                                f"\r{x264_encoded_frame:>9}/{total_frame_cnt:<9} "
                                f"{display_percent_str:^10} {ave_fps:^12.2f} "
                                f"{display_bitrate_str:^18} "
                                f"{display_remain_str:^14}"
                            ),
                            end="",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            (
                                f"\rplease waiting for x264, vspipe processed "
                                f"{vspipe_processed_frame} frames"
                            ),
                            end="",
                            file=sys.stderr,
                        )

            print("\n", end="", file=sys.stderr)
            if (
                process.returncode == 0
                and all_encoded_frame == total_frame_cnt
            ):
                encode_info_str: str = (
                    f"transcode x264: "
                    f"total frame cnt: {total_frame_cnt}, "
                    f"encoded frame cnt: {all_encoded_frame}, "
                    f"encoded fps: {encode_fps}, "
                    f"encoded bitrate: {encode_bitrate}, "
                )
                print(encode_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, encode_info_str)
                end_info_str: str = (
                    f"transcode x264: "
                    f"transcoding {output_video_filepath} successfully."
                )
                print(end_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, end_info_str)
                break

            transcode_detail_info_str: str = (
                f"transcode x264:"
                f"return code: {process.returncode} "
                f"encoded frame cnt: {all_encoded_frame} "
                f"total frame cnt: {total_frame_cnt}"
            )
            g_logger.log(logging.ERROR, transcode_detail_info_str)
            stderr_str: str = "".join(stderr_lines_deque)
            stderr_error_info_str: str = (
                f"transcode x264: " f"stderror:\n{stderr_str}"
            )
            g_logger.log(logging.ERROR, stderr_error_info_str)
            transcode_error_str: str = (
                f"transcode x264: "
                f"transcoding {output_video_filepath} unsuccessfully, "
                f"try again."
            )
            g_logger.log(logging.ERROR, transcode_error_str)

        return output_video_filepath, encode_fps, encode_bitrate


class NvencVspipeVideoTranscoding(VspipeVideoTranscoding):

    necessary_vspipe_nvenc_template_set: set = {
        "{{vspipe_exe_filepath}}",
        "{{input_vpy_filepath}}",
        "{{nvenc_exe_filepath}}",
        "{{output_video_filepath}}",
    }
    nvenc_exe_filename: str = "NVEncC64.exe"

    nvenc_full_range_param: str = "--fullrange"

    def __init__(
        self,
        input_video_filepath: str,
        frame_server_template_filepath: str,
        frame_server_script_cache_dir: str,
        frame_server_script_filename: str,
        frame_server_template_config: dict,
        output_video_dir: str,
        output_video_filename: str,
        transcoding_cmd_param_template: list,
        other_config: dict,
        vspipe_exe_dir="",
        nvenc_exe_dir="",
    ):
        if not isinstance(nvenc_exe_dir, str):
            raise TypeError(
                f"type of nvenc_exe_dir must be str "
                f"instead of {type(nvenc_exe_dir)}"
            )
        if nvenc_exe_dir:
            if not os.path.isdir(nvenc_exe_dir):
                raise DirNotFoundError(
                    f"nvenc dir cannot be found with {nvenc_exe_dir}"
                )
            all_filename_list: list = os.listdir(nvenc_exe_dir)
            if self.nvenc_exe_filename not in all_filename_list:
                raise FileNotFoundError(
                    f"{self.nvenc_exe_filename} cannot be found in "
                    f"{nvenc_exe_dir}"
                )
        else:
            if not check_file_environ_path({self.nvenc_exe_filename}):
                raise FileNotFoundError(
                    f"{self.nvenc_exe_filename} cannot be found in "
                    f"environment path"
                )
        self._nvenc_exe_dir = nvenc_exe_dir

        super(NvencVspipeVideoTranscoding, self).__init__(
            input_video_filepath,
            frame_server_template_filepath,
            frame_server_script_cache_dir,
            frame_server_script_filename,
            frame_server_template_config,
            output_video_dir,
            output_video_filename,
            transcoding_cmd_param_template,
            other_config,
            vspipe_exe_dir,
        )
        for vspipe_nvenc_template in self.necessary_vspipe_nvenc_template_set:
            if (
                vspipe_nvenc_template
                not in self._transcoding_cmd_param_template
            ):
                raise MissTemplateError(
                    message=(
                        f"transcoding_cmd_param_template misses "
                        f"template {vspipe_nvenc_template}"
                    ),
                    missing_template=vspipe_nvenc_template,
                )

    def transcode(self) -> str:
        self._generate_vpy_script()

        vspipe_nvenc_cmd_param_list = self._transcoding_cmd_param_template
        program_param_dict: dict = {}

        self._update_transcoding_cmd_template(program_param_dict)

        vspipe_nvenc_cmd_param_list = replace_param_template_list(
            vspipe_nvenc_cmd_param_list, program_param_dict
        )

        codec_key_list: list = ["-c", "--codec"]
        codec_value_h264: str = "h264"
        codec_value_h265: str = "hevc"

        codec_exist_bool: bool = False
        codec_key_index: int = -1
        for param in codec_key_list:
            if param in set(vspipe_nvenc_cmd_param_list):
                codec_exist_bool = True
                codec_key_index = vspipe_nvenc_cmd_param_list.index(param)
                break

        assert (not codec_exist_bool and codec_key_index == -1) or (
            codec_exist_bool and codec_key_index > -1
        ), (
            "codec_exist_bool and codec_key_index must be "
            "significant simultaneously"
        )

        if codec_exist_bool:
            codec_value: str = vspipe_nvenc_cmd_param_list[codec_key_index + 1]
            if codec_value == codec_value_h265:
                output_video_suffix: str = self.h265_extension
            elif codec_value == codec_value_h264:
                output_video_suffix: str = self.h264_extension
            else:
                raise RuntimeError("codec must be hevc or h264")
        else:
            output_video_suffix: str = self.h264_extension

        nvenc_exe_filepath: str = os.path.join(
            self._nvenc_exe_dir, self.nvenc_exe_filename
        )

        output_video_fullname: str = (
            self._output_video_filename + output_video_suffix
        )
        output_video_filepath: str = os.path.join(
            self._output_video_dir, output_video_fullname
        )

        program_param_dict: dict = {
            "vspipe_exe_filepath": self._vspipe_exe_filepath,
            "input_vpy_filepath": self._transcoding_vpy_filepath,
            "nvenc_exe_filepath": nvenc_exe_filepath,
            "output_video_filepath": output_video_filepath,
        }

        vspipe_nvenc_cmd_param_list = replace_param_template_list(
            vspipe_nvenc_cmd_param_list, program_param_dict
        )
        nvenc_full_range_param: str = "--fullrange"
        if nvenc_full_range_param in set(vspipe_nvenc_cmd_param_list):
            if not self._output_full_range_bool:
                warnings.warn(
                    (
                        f"whether to output full range yuv is different "
                        f"between config "
                        f"output_full_range_bool "
                        f"{self._output_full_range_bool} and nvenc cmd param "
                        f"{nvenc_full_range_param}"
                    ),
                    RuntimeWarning,
                )
        else:
            if self._output_full_range_bool:
                nvenc_full_range_param.append(nvenc_full_range_param)
        width: int = self._vpy_template_dict["output_width"]
        height: int = self._vpy_template_dict["output_height"]
        vspipe_nvenc_cmd_param_list += self.color_matrix_cmd_params(
            width,
            height,
            self._frame_server_template_config["output_bit_depth"],
        )
        self._process_fps_cmd_param(
            vspipe_nvenc_cmd_param_list, self._other_config
        )
        self._process_sar_cmd_param(
            vspipe_nvenc_cmd_param_list, self._other_config
        )
        self._process_hdr_cmd_param(
            vspipe_nvenc_cmd_param_list, self._other_config
        )

        log_param: str = "--log"
        log_suffix: str = ".log"
        log_file_dir: str = self._frame_server_script_cache_dir
        log_file_fullname: str = self._output_video_filename + log_suffix
        log_filepath: str = os.path.join(log_file_dir, log_file_fullname)
        log_param_value: str = log_filepath
        if log_param not in set(vspipe_nvenc_cmd_param_list):
            vspipe_nvenc_cmd_param_list += [log_param, log_param_value]

        if os.path.isfile(log_filepath):
            os.remove(log_filepath)

        vspipe_nvenc_cmd_param_list = self._cmd_param_list_element_2_str(
            vspipe_nvenc_cmd_param_list
        )

        nvenc_param_debug_str: str = (
            f"transcode vspipe nvenc: param: "
            f"{subprocess.list2cmdline(vspipe_nvenc_cmd_param_list)}"
        )
        g_logger.log(logging.DEBUG, nvenc_param_debug_str)

        start_info_str: str = (
            f"transcode vspipe nvenc: starting transcoding "
            f"{output_video_filepath}"
        )

        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        while True:
            process = subprocess.Popen(vspipe_nvenc_cmd_param_list, shell=True)

            process.communicate()

            if process.returncode == 0:
                end_info_str: str = (
                    f"transcode vspipe nvenc: "
                    f"transcoding {output_video_filepath} successfully."
                )
                print(end_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, end_info_str)
                break
            transcode_error_str: str = (
                f"transcode vspipe nvenc: "
                f"transcoding {output_video_filepath} "
                f"unsuccessfully, try again."
            )
            g_logger.log(logging.ERROR, transcode_error_str)

            warning_str: str = (
                f"transcode nvenc:"
                f"transcoding error, if this waring occurs repeatly "
                f"please check frameserver script or parameter."
            )
            warnings.warn(warning_str, RuntimeWarning)
            g_logger.log(logging.WARNING, warning_str)

        return output_video_filepath


def get_fpsnum_and_fpsden(fps: str):
    if not isinstance(fps, str):
        fps = str(fps)

    fps_info_dict: dict = dict(fps_num=0, fps_den=0)

    if "/" in fps:
        fps_data_list: list = fps.split("/")
        if len(fps_data_list) != 2:
            raise ValueError(
                f"len(fps_data_list) != 2 : " f"{len(fps_data_list) != 2}"
            )
        fps_info_dict["fps_num"] = int(fps_data_list[0])
        fps_info_dict["fps_den"] = int(fps_data_list[1])
    elif fps.replace(".", "").isdigit():
        fps_float = float(fps)
        if int(fps_float) == fps_float:
            fps_info_dict["fps_num"] = int(fps_float)
            fps_info_dict["fps_den"] = 1
        else:
            fps_info_dict["fps_num"] = int(fps_float * 1000)
            fps_info_dict["fps_den"] = 1000
    else:
        raise ValueError(f"unknown fps: {fps}")

    reduced_fps_dict: dict = get_reduced_fraction(
        numerator=fps_info_dict["fps_num"],
        denominator=fps_info_dict["fps_den"],
    )

    fps_info_dict["fps_num"] = reduced_fps_dict["numerator"]
    fps_info_dict["fps_den"] = reduced_fps_dict["denominator"]

    FpsInfo: namedtuple = namedtuple("FpsInfo", sorted(fps_info_dict))
    fps_info: namedtuple = FpsInfo(**fps_info_dict)

    return fps_info
