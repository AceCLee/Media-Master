"""
    transcode.py transcode audio stream
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

from pymediainfo import MediaInfo

from ..error import DirNotFoundError, RangeError
from ..util import check_file_environ_path, replace_param_template_list

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def get_input_audio_info(audio_filepath: str) -> dict:
    media_info_list: list = MediaInfo.parse(audio_filepath).to_data()["tracks"]
    audio_info_dict: dict = next(
        (track for track in media_info_list if track["track_type"] == "Audio"),
        None,
    )

    bit_depth: int = int(
        audio_info_dict["bit_depth"]
    ) if "bit_depth" in audio_info_dict.keys() else 16

    info_dict: dict = dict(bit_depth=bit_depth)

    return info_dict


def transcode_audio_flac(
    input_audio_filepath: str,
    output_audio_dir: str,
    output_audio_name: str,
    flac_exe_cmd_param_template: list,
    delete_input_file_bool=False,
    flac_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> str:
    if not isinstance(input_audio_filepath, str):
        raise TypeError(
            f"type of input_audio_filepath must be str "
            f"instead of {type(input_audio_filepath)}"
        )

    if not isinstance(output_audio_dir, str):
        raise TypeError(
            f"type of output_audio_dir must be str "
            f"instead of {type(output_audio_dir)}"
        )

    if not isinstance(output_audio_name, str):
        raise TypeError(
            f"type of output_audio_name must be str "
            f"instead of {type(output_audio_name)}"
        )

    if not isinstance(flac_exe_cmd_param_template, list):
        raise TypeError(
            f"type of flac_exe_cmd_param_template must be list "
            f"instead of {type(flac_exe_cmd_param_template)}"
        )

    if not isinstance(flac_exe_file_dir, str):
        raise TypeError(
            f"type of flac_exe_file_dir must be str "
            f"instead of {type(flac_exe_file_dir)}"
        )
    if not os.path.exists(input_audio_filepath):
        raise FileNotFoundError(
            f"input audio file cannot be found with {input_audio_filepath}"
        )

    flac_exe_name: str = "flac.exe"
    flac_exe_name_set: set = {flac_exe_name}
    if flac_exe_file_dir:
        if not os.path.isdir(flac_exe_file_dir):
            raise DirNotFoundError(
                f"flac dir cannot be found with {flac_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(flac_exe_file_dir)
        for flac_exe_name in flac_exe_name_set:
            if flac_exe_name not in all_filename_list:
                raise FileNotFoundError(
                    f"{flac_exe_name} cannot be found in "
                    f"{flac_exe_file_dir}"
                )
    else:
        if not check_file_environ_path(flac_exe_name_set):
            raise FileNotFoundError(
                f"at least one of {flac_exe_name_set} cannot "
                f"be found in environment path"
            )

    ffmpeg_exe_name: str = "ffmpeg.exe"
    ffmpeg_exe_name_set: set = {ffmpeg_exe_name}
    if ffmpeg_exe_file_dir:
        if not os.path.isdir(ffmpeg_exe_file_dir):
            raise DirNotFoundError(
                f"ffmpeg dir cannot be found with {ffmpeg_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(ffmpeg_exe_file_dir)
        for ffmpeg_exe_name in ffmpeg_exe_name_set:
            if ffmpeg_exe_name not in all_filename_list:
                raise FileNotFoundError(
                    f"{ffmpeg_exe_name} cannot be found in "
                    f"{ffmpeg_exe_file_dir}"
                )
    else:
        if not check_file_environ_path(ffmpeg_exe_name_set):
            raise FileNotFoundError(
                f"at least one of {ffmpeg_exe_name_set} cannot "
                f"be found in environment path"
            )
    if not os.path.exists(output_audio_dir):
        os.makedirs(output_audio_dir)

    flac_extension: str = ".flac"
    output_audio_fullname: str = output_audio_name + flac_extension
    output_filepath: str = os.path.join(
        output_audio_dir, output_audio_fullname
    )

    flac_exe_filepath: str = os.path.join(flac_exe_file_dir, flac_exe_name)
    ffmpeg_exe_filepath: str = os.path.join(
        ffmpeg_exe_file_dir, ffmpeg_exe_name
    )

    info_dict: dict = get_input_audio_info(input_audio_filepath)

    program_param_dict = {
        "ffmpeg_exe_filepath": ffmpeg_exe_filepath,
        "flac_exe_filepath": flac_exe_filepath,
        "input_audio_filepath": input_audio_filepath,
        "output_filepath": output_filepath,
        "ffmpeg_wav_audio_codec": f"pcm_s{info_dict['bit_depth']}le",
    }

    flac_exe_cmd_param = replace_param_template_list(
        flac_exe_cmd_param_template, program_param_dict
    )

    flac_param_debug_str: str = (
        f"audio flac: param: {subprocess.list2cmdline(flac_exe_cmd_param)}"
    )
    g_logger.log(logging.DEBUG, flac_param_debug_str)

    start_info_str: str = f"audio flac: starting encoding {output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process: subprocess.Popen = subprocess.Popen(
        flac_exe_cmd_param, shell=True
    )

    process.communicate()

    if process.returncode == 0:
        end_info_str: str = (
            f"audio flac: transcode {input_audio_filepath} to "
            f"{output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"audio flac: transcode {input_audio_filepath} to "
            f"{output_filepath} unsuccessfully!"
        )
    if delete_input_file_bool and not os.path.samefile(
        input_audio_filepath, output_filepath
    ):
        delete_info_str: str = f"audio flac: delete {input_audio_filepath}"

        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(input_audio_filepath)

    return output_filepath


def transcode_audio_ffmpeg(
    input_audio_filepath: str,
    output_audio_dir: str,
    output_audio_name: str,
    output_extension: str,
    delete_input_file_bool=False,
    ffmpeg_exe_file_dir="",
) -> str:
    if not isinstance(input_audio_filepath, str):
        raise TypeError(
            f"type of input_audio_filepath must be str "
            f"instead of {type(input_audio_filepath)}"
        )

    if not isinstance(output_audio_dir, str):
        raise TypeError(
            f"type of output_audio_dir must be str "
            f"instead of {type(output_audio_dir)}"
        )

    if not isinstance(output_audio_name, str):
        raise TypeError(
            f"type of output_audio_name must be str "
            f"instead of {type(output_audio_name)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.isfile(input_audio_filepath):
        raise FileNotFoundError(
            f"input audio file cannot be found with {input_audio_filepath}"
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
                f"{ffmpeg_exe_filename} cannot be found in environment path"
            )
    if not os.path.isdir(output_audio_dir):
        os.makedirs(output_audio_dir)

    audio_filename: str = output_audio_name + output_extension
    output_audio_filepath: str = os.path.join(output_audio_dir, audio_filename)

    ffmpeg_exe_filepath: str = os.path.join(
        ffmpeg_exe_file_dir, ffmpeg_exe_filename
    )
    input_key: str = "-i"
    input_value: str = input_audio_filepath
    overwrite_key: str = "-y"
    output_value: str = output_audio_filepath

    args_list: list = [ffmpeg_exe_filepath, input_key, input_value]

    info_dict: dict = get_input_audio_info(input_audio_filepath)

    if info_dict["bit_depth"] > 16 and output_extension == ".wav":
        args_list += ["-codec:a", f"pcm_s{info_dict['bit_depth']}le"]

    args_list += [overwrite_key, output_value]

    param_debug_str: str = (
        f"transcode audio: param:" f"{subprocess.list2cmdline(args_list)}"
    )
    g_logger.log(logging.DEBUG, param_debug_str)

    start_info_str: str = (
        f"transcode audio: transcode {input_audio_filepath} to "
        f"{output_audio_filepath}"
    )
    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process: subprocess.Popen = subprocess.Popen(args=args_list)

    process.communicate()

    if process.returncode == 0:
        end_info_str: str = (
            f"transcode audio: transcode {input_audio_filepath} to "
            f"{output_audio_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"transcode audio: transcode {input_audio_filepath} to "
            f"{output_audio_filepath} unsuccessfully!"
        )

    if delete_input_file_bool and not os.path.samefile(
        input_audio_filepath, output_audio_filepath
    ):
        delete_info_str: str = f"transcode audio: delete {input_audio_filepath}"

        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(input_audio_filepath)

    return output_audio_filepath


def transcode_audio_opus(
    input_audio_filepath: str,
    output_audio_dir: str,
    output_audio_name: str,
    opus_exe_config_list: list,
    bitrate=128.0,
    computational_complexity=10,
    expect_loss=0,
    delete_input_file_bool=False,
    opus_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> str:
    if not isinstance(input_audio_filepath, str):
        raise TypeError(
            f"type of input_audio_filepath must be str "
            f"instead of {type(input_audio_filepath)}"
        )

    if not isinstance(output_audio_dir, str):
        raise TypeError(
            f"type of output_audio_dir must be str "
            f"instead of {type(output_audio_dir)}"
        )

    if not isinstance(output_audio_name, str):
        raise TypeError(
            f"type of output_audio_name must be str "
            f"instead of {type(output_audio_name)}"
        )

    if not isinstance(opus_exe_config_list, list):
        raise TypeError(
            f"type of opus_exe_config_list must be list "
            f"instead of {type(opus_exe_config_list)}"
        )

    if (not isinstance(bitrate, float)) and (not isinstance(bitrate, int)):
        raise TypeError(
            f"type of bitrate must be float or int "
            f"instead of {type(bitrate)}"
        )

    if not isinstance(computational_complexity, int):
        raise TypeError(
            f"type of computational_complexity must be int "
            f"instead of {type(computational_complexity)}"
        )

    if not isinstance(expect_loss, int):
        raise TypeError(
            f"type of expect_loss must be int "
            f"instead of {type(expect_loss)}"
        )

    if not isinstance(opus_exe_file_dir, str):
        raise TypeError(
            f"type of opus_exe_file_dir must be str "
            f"instead of {type(opus_exe_file_dir)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.exists(input_audio_filepath):
        raise FileNotFoundError(
            f"input audio file cannot be found with {input_audio_filepath}"
        )

    opusenc_exe_name: str = "opusenc.exe"
    opusdec_exe_name: str = "opusdec.exe"
    opus_exe_name_set: set = {opusenc_exe_name, opusdec_exe_name}
    if opus_exe_file_dir:
        if not os.path.isdir(opus_exe_file_dir):
            raise DirNotFoundError(
                f"opus dir cannot be found with {opus_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(opus_exe_file_dir)
        for opus_exe_name in opus_exe_name_set:
            if opus_exe_name not in all_filename_list:
                raise FileNotFoundError(
                    f"{opus_exe_name} cannot be found in "
                    f"{opus_exe_file_dir}"
                )
    else:
        if not check_file_environ_path(opus_exe_name_set):
            raise FileNotFoundError(
                f"at least one of {opus_exe_name_set} cannot "
                f"be found in environment path"
            )
    if bitrate < 0:
        raise RangeError(
            message="value of bitrate can not be negative",
            valid_range="[0,inf]",
        )

    if computational_complexity < 0 or computational_complexity > 10:
        raise RangeError(
            message="value of computational_complexity must in [0,10]",
            valid_range="[0,10]",
        )

    if expect_loss < 0 or expect_loss > 100:
        raise RangeError(
            message="value of computational_complexity must in [0,100]",
            valid_range="[0,100]",
        )
    if not os.path.exists(output_audio_dir):
        os.makedirs(output_audio_dir)

    opusenc_support_suffix_set: set = {".opus", ".flac", ".wav"}
    input_audio_filename: str = os.path.basename(input_audio_filepath)
    input_audio_filename_ext: str = os.path.splitext(input_audio_filename)[1]
    opusenc_unsupport_bool: bool = input_audio_filename_ext not in opusenc_support_suffix_set
    if opusenc_unsupport_bool:

        input_audio_filepath = transcode_audio_ffmpeg(
            input_audio_filepath=input_audio_filepath,
            output_audio_dir=output_audio_dir,
            output_audio_name=output_audio_name,
            output_extension=".flac",
            delete_input_file_bool=delete_input_file_bool,
            ffmpeg_exe_file_dir=ffmpeg_exe_file_dir,
        )

    opus_suffix: str = ".opus"
    output_audio_fullname: str = output_audio_name + opus_suffix
    output_filepath: str = os.path.join(
        output_audio_dir, output_audio_fullname
    )

    opusenc_exe_filepath: str = os.path.join(
        opus_exe_file_dir, opusenc_exe_name
    )

    opusdec_exe_filepath: str = os.path.join(
        opus_exe_file_dir, opusdec_exe_name
    )

    input_opus_bool: bool = input_audio_filepath.endswith(opus_suffix)
    current_opus_exe_config_list: list = []
    if input_opus_bool:
        opus_exe_config_list_copy: list = copy.deepcopy(opus_exe_config_list)
        current_opus_exe_config_list = [
            opusdec_exe_filepath,
            "--force-wav",
            input_audio_filepath,
            "-",
            "|",
        ]
        opusenc_exe_config_list = opus_exe_config_list_copy
        current_opus_exe_config_list += opusenc_exe_config_list
    else:
        current_opus_exe_config_list = copy.deepcopy(opus_exe_config_list)

    program_param_dict = {
        "opusenc_exe_filepath": opusenc_exe_filepath,
        "input_audio_filepath": input_audio_filepath
        if not input_opus_bool
        else "-",
        "output_filepath": output_filepath,
    }

    current_opus_exe_config_list = replace_param_template_list(
        current_opus_exe_config_list, program_param_dict
    )

    opus_param_debug_str: str = f"audio opus: param:\
{subprocess.list2cmdline(current_opus_exe_config_list)}"
    g_logger.log(logging.DEBUG, opus_param_debug_str)

    start_info_str: str = f"audio opus: starting encoding {output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process: subprocess.Popen = subprocess.Popen(
        current_opus_exe_config_list,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    opusenc_infor_re_exp: str = "(\\d{1,3})% \
    (\\d{2}):(\\d{2}):(\\d{2})\\.(\\d{2}).*?(\\d+\\.{0,1}\\d{0,1}) kbit/s"

    opusdec_enc_time_infor_re_exp: str = r"(\d{2}):(\d{2}):(\d{2})"
    opusdec_enc_infor_re_exp: str = (
        r"(\d{2}):(\d{2}):(\d{2}).*?(\d+\.{0,1}\d{0,1}) kbit/s"
    )

    bitrate: float = 0.0
    while process.poll() is None:
        current_line: str = process.stderr.readline()
        opusenc_infor_re_result: re.Match = re.search(
            opusenc_infor_re_exp, current_line
        )
        opusdec_enc_time_infor_re_result: re.Match = re.search(
            opusdec_enc_time_infor_re_exp, current_line
        )
        opusdec_enc_infor_re_result: re.Match = re.search(
            opusdec_enc_infor_re_exp, current_line
        )

        if opusenc_infor_re_result:
            percent = float(opusenc_infor_re_result.group(1))
            hour = int(opusenc_infor_re_result.group(2))
            minute = int(opusenc_infor_re_result.group(3))
            second = int(opusenc_infor_re_result.group(4))
            ten_milisecond = int(opusenc_infor_re_result.group(5))
            bitrate = float(opusenc_infor_re_result.group(6))

            print(
                f"\rTranscoding opus ... Percent: {percent:.2f}% \
Time: {hour:0>2}:{minute:0>2}:{second:0>2}.\
{ten_milisecond:0>2} Bitrate: {bitrate:.2f}kbit/s",
                end="",
                file=sys.stderr,
            )

        elif opusdec_enc_infor_re_result:
            hour = int(opusdec_enc_infor_re_result.group(1))
            minute = int(opusdec_enc_infor_re_result.group(2))
            second = int(opusdec_enc_infor_re_result.group(3))
            bitrate = float(opusdec_enc_infor_re_result.group(4))
            print(
                f"\rTranscoding opus ... : Time: {hour:0>2}:{minute:0>2}:\
{second:0>2} Bitrate: {bitrate:.2f}kbit/s",
                end="",
                file=sys.stderr,
            )
        elif opusdec_enc_time_infor_re_result:
            hour = int(opusdec_enc_time_infor_re_result.group(1))
            minute = int(opusdec_enc_time_infor_re_result.group(2))
            second = int(opusdec_enc_time_infor_re_result.group(3))
            print(
                f"\rTranscoding opus ... : Time: {hour:0>2}:{minute:0>2}:\
{second:0>2} Bitrate: {bitrate:.2f}kbit/s",
                end="",
                file=sys.stderr,
            )

    print("\n", end="", file=sys.stderr)

    if process.returncode == 0:
        end_info_str: str = f"audio opus: transcode {input_audio_filepath} to \
{output_filepath} successfully."
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"audio opus: transcode {input_audio_filepath} to \
{output_filepath} unsuccessfully!"
        )
    if opusenc_unsupport_bool:
        delete_info_str: str = f"audio opus: delete {input_audio_filepath}"

        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(input_audio_filepath)
    else:
        if delete_input_file_bool and not os.path.samefile(
            input_audio_filepath, output_filepath
        ):
            delete_info_str: str = f"audio opus: delete {input_audio_filepath}"

            print(delete_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, delete_info_str)
            os.remove(input_audio_filepath)

    return output_filepath


def transcode_audio_qaac(
    input_audio_filepath: str,
    output_audio_dir: str,
    output_audio_name: str,
    qaac_exe_cmd_param_template: list,
    delete_input_file_bool=False,
    qaac_exe_file_dir="",
    ffmpeg_exe_file_dir="",
) -> str:
    if not isinstance(input_audio_filepath, str):
        raise TypeError(
            f"type of input_audio_filepath must be str "
            f"instead of {type(input_audio_filepath)}"
        )

    if not isinstance(output_audio_dir, str):
        raise TypeError(
            f"type of output_audio_dir must be str "
            f"instead of {type(output_audio_dir)}"
        )

    if not isinstance(output_audio_name, str):
        raise TypeError(
            f"type of output_audio_name must be str "
            f"instead of {type(output_audio_name)}"
        )

    if not isinstance(qaac_exe_cmd_param_template, list):
        raise TypeError(
            f"type of qaac_exe_cmd_param_template must be list "
            f"instead of {type(qaac_exe_cmd_param_template)}"
        )

    if not isinstance(qaac_exe_file_dir, str):
        raise TypeError(
            f"type of qaac_exe_file_dir must be str "
            f"instead of {type(qaac_exe_file_dir)}"
        )

    if not isinstance(ffmpeg_exe_file_dir, str):
        raise TypeError(
            f"type of ffmpeg_exe_file_dir must be str "
            f"instead of {type(ffmpeg_exe_file_dir)}"
        )
    if not os.path.exists(input_audio_filepath):
        raise FileNotFoundError(
            f"input audio file cannot be found with {input_audio_filepath}"
        )

    qaac_exe_name: str = "qaac64.exe"
    qaac_exe_name_set: set = {qaac_exe_name}
    if qaac_exe_file_dir:
        if not os.path.isdir(qaac_exe_file_dir):
            raise DirNotFoundError(
                f"qaac dir cannot be found with {qaac_exe_file_dir}"
            )
        all_filename_list: list = os.listdir(qaac_exe_file_dir)
        for qaac_exe_name in qaac_exe_name_set:
            if qaac_exe_name not in all_filename_list:
                raise FileNotFoundError(
                    f"{qaac_exe_name} cannot be found in "
                    f"{qaac_exe_file_dir}"
                )
    else:
        if not check_file_environ_path(qaac_exe_name_set):
            raise FileNotFoundError(
                f"at least one of {qaac_exe_name_set} cannot "
                f"be found in environment path"
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
                f"{ffmpeg_exe_filename} cannot be found in environment path"
            )
    if not os.path.exists(output_audio_dir):
        os.makedirs(output_audio_dir)

    qaac_extension: str = ".aac"
    output_audio_fullname: str = output_audio_name + qaac_extension
    output_filepath: str = os.path.join(
        output_audio_dir, output_audio_fullname
    )

    ffmpeg_exe_filepath: str = os.path.join(
        ffmpeg_exe_file_dir, ffmpeg_exe_filename
    )
    qaac_exe_filepath: str = os.path.join(qaac_exe_file_dir, qaac_exe_name)

    info_dict: dict = get_input_audio_info(input_audio_filepath)

    program_param_dict = {
        "ffmpeg_exe_filepath": ffmpeg_exe_filepath,
        "qaac_exe_filepath": qaac_exe_filepath,
        "input_audio_filepath": input_audio_filepath,
        "output_filepath": output_filepath,
        "ffmpeg_wav_audio_codec": f"pcm_s{info_dict['bit_depth']}le",
    }

    qaac_exe_cmd_param = replace_param_template_list(
        qaac_exe_cmd_param_template, program_param_dict
    )

    qaac_param_debug_str: str = f"audio qaac: param:\
{subprocess.list2cmdline(qaac_exe_cmd_param)}"
    g_logger.log(logging.DEBUG, qaac_param_debug_str)

    start_info_str: str = f"audio qaac: starting encoding {output_filepath}"

    print(start_info_str, file=sys.stderr)
    g_logger.log(logging.INFO, start_info_str)

    process: subprocess.Popen = subprocess.Popen(
        qaac_exe_cmd_param, shell=True
    )

    process.wait()

    if process.returncode == 0:
        end_info_str: str = (
            f"audio qaac: transcode {input_audio_filepath} to "
            f"{output_filepath} successfully."
        )
        print(end_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, end_info_str)
    else:
        raise ChildProcessError(
            f"audio qaac: transcode {input_audio_filepath} to "
            f"{output_filepath} unsuccessfully!"
        )
    if delete_input_file_bool and not os.path.samefile(
        input_audio_filepath, output_filepath
    ):
        delete_info_str: str = f"audio qaac: delete {input_audio_filepath}"

        print(delete_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, delete_info_str)
        os.remove(input_audio_filepath)

    return output_filepath


def decode_flac_to_wav(
    input_audio_filepath: str,
    output_audio_dir: str,
    output_audio_name: str,
    flac_exe_file_dir="",
) -> str:
    if not isinstance(input_audio_filepath, str):
        raise TypeError(
            f"type of input_audio_filepath must be str \
instead of {type(input_audio_filepath)}"
        )

    if not isinstance(output_audio_dir, str):
        raise TypeError(
            f"type of output_audio_dir must be str \
instead of {type(output_audio_dir)}"
        )

    if not isinstance(output_audio_name, str):
        raise TypeError(
            f"type of output_audio_name must be str \
instead of {type(output_audio_name)}"
        )

    if not isinstance(flac_exe_file_dir, str):
        raise TypeError(
            f"type of flac_exe_file_dir must be str \
instead of {type(flac_exe_file_dir)}"
        )
    if not os.path.exists(input_audio_filepath):
        raise FileNotFoundError(
            f"input audio file cannot be found with {input_audio_filepath}"
        )
    if not os.path.exists(output_audio_dir):
        os.makedirs(output_audio_dir)

    flac_exe_name = "flac.exe"
    flac_exe_filepath = os.path.join(flac_exe_file_dir, flac_exe_name)

    wav_suffix = ".wav"
    output_audio_fullname = output_audio_name + wav_suffix
    output_filepath = os.path.join(output_audio_dir, output_audio_fullname)

    args_list = [
        flac_exe_filepath,
        "--decode",
        input_audio_filepath,
        "--output-name",
        output_filepath,
    ]

    process = subprocess.Popen(
        args_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    stdout_data, stderr_data = process.communicate()
    if process.returncode == 0:
        print(
            "{} has been decoded successfully.".format(output_filepath),
            file=sys.stderr,
        )
    else:
        raise ChildProcessError(
            "decode {} unsuccessfully.".format(output_filepath)
        )
