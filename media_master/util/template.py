"""
    template.py template module of media_master
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
import re
import copy
from .config import load_config, save_config

G_PARAM_RE_EXP: str = "{{\\s*(\\S+)\\s*}}"


def is_template(string: str, param_re_exp=G_PARAM_RE_EXP):
    return re.fullmatch(param_re_exp, str(string)) is not None


def replace_config_template_dict(
    config_dict, program_param_dict, param_re_exp=G_PARAM_RE_EXP
):
    modified_config_dict: dict = copy.deepcopy(config_dict)
    for key in modified_config_dict.keys():
        value = str(modified_config_dict[key])
        re_result = re.fullmatch(param_re_exp, value)
        if re_result:
            modified_config_dict[key] = program_param_dict[re_result.group(1)]
    return modified_config_dict


def replace_param_template_list(
    param_list, program_param_dict, param_re_exp=G_PARAM_RE_EXP
):
    modified_param_list: dict = copy.deepcopy(param_list)
    for index, param in enumerate(modified_param_list):
        re_result = re.fullmatch(param_re_exp, param)
        if re_result:
            modified_param_list[index] = program_param_dict[re_result.group(1)]
    return modified_param_list


def generate_vpy_file(
    vpy_template_dict: dict,
    vpy_content_template_filepath: str,
    vpy_files_dir: str,
    vpy_filename: str,
):
    if not os.path.exists(vpy_files_dir):
        os.makedirs(vpy_files_dir)

    vpy_file_suffix = ".vpy"

    content_template_str = ""
    with open(vpy_content_template_filepath, "r", encoding="utf-8") as file:
        content_template_str = file.read()

    assert content_template_str, "content of {} is empty!".format(
        vpy_content_template_filepath
    )

    content_str = content_template_str
    for key in vpy_template_dict.keys():
        content_str = content_str.replace(
            "{{" + key + "}}", str(vpy_template_dict[key])
        )

    vpy_file_fullname = vpy_filename + vpy_file_suffix
    vpy_filepath = os.path.join(vpy_files_dir, vpy_file_fullname)

    with open(vpy_filepath, "w", encoding="utf-8") as file:
        file.write(content_str)

    return vpy_filepath


def generate_single_transcode_config(
    single_transcode_config_template_json_filepath: str,
    output_transcode_config_template_json_filepath: str,
    input_output_info_list: list,
):
    input_config_dict: dict = load_config(
        single_transcode_config_template_json_filepath
    )
    output_config_list: list = []
    for input_output_info in input_output_info_list:
        input_filepath: str = input_output_info["input_filepath"]
        output_file_dir: str = input_output_info["output_file_dir"]
        output_filename: str = input_output_info["output_filename"]
        new_config_dict: dict = copy.deepcopy(input_config_dict)
        new_config_dict["type_related_config"][
            "input_video_filepath"
        ] = input_filepath
        new_config_dict["type_related_config"][
            "output_video_dir"
        ] = output_file_dir
        new_config_dict["type_related_config"][
            "output_video_name"
        ] = output_filename
        output_config_list.append(new_config_dict)
    output_dict: dict = {"result": output_config_list}
    save_config(output_transcode_config_template_json_filepath, output_dict)


