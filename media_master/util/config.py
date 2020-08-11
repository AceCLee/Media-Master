"""
    config.py config module of media_master
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

import json
import os
from .constant import global_constant
from ..error import RangeError
import yaml
import pyhocon


def load_config(config_filepath):
    if not isinstance(config_filepath, str):
        raise TypeError(
            f"type of config_filepath must be str "
            f"instead of {type(config_filepath)}"
        )
    if not os.path.isfile(config_filepath):
        raise FileNotFoundError(
            f"input config file cannot be found with {config_filepath}"
        )

    constant = global_constant()

    available_config_format_set: set = constant.available_config_format_set
    available_config_format_extension_dict: dict = constant.available_config_format_extension_dict
    available_config_format_extension_set: set = set()
    for extension_set in available_config_format_extension_dict.values():
        available_config_format_extension_set |= extension_set

    config_full_filename: str = os.path.basename(config_filepath)
    config_filename, config_extension = os.path.splitext(config_full_filename)

    if config_extension not in available_config_format_extension_set:
        raise RangeError(
            message=(f"Unknown config_extension: {config_extension}"),
            valid_range=str(available_config_format_extension_set),
        )

    config_format: str = ""
    for current_config_format in available_config_format_set:
        if (
            config_extension
            in available_config_format_extension_dict[current_config_format]
        ):
            config_format = current_config_format
            break

    if not config_format:
        raise ValueError(f"it is not possible to run this code.")

    config_data_dict: dict = {}
    with open(config_filepath, "r", encoding="utf-8") as file:
        if config_format == "json":
            config_data_dict = json.loads(file.read())
        elif config_format == "yaml":
            config_data_dict = yaml.load(file, Loader=yaml.SafeLoader)
        elif config_format == "hocon":
            config_data_dict = pyhocon.ConfigFactory.parse_string(
                file.read()
            ).as_plain_ordered_dict()
        else:
            raise ValueError(f"it is not possible to run this code.")

    return config_data_dict


def save_config(config_json_filepath: str, config_dict: dict):
    if not isinstance(config_json_filepath, str):
        raise TypeError(
            f"type of config_json_filepath must be str "
            f"instead of {type(config_json_filepath)}"
        )
    if not isinstance(config_dict, dict):
        raise TypeError(
            f"type of config_dict must be dict "
            f"instead of {type(config_dict)}"
        )
    config_json_dir = os.path.abspath(os.path.dirname(config_json_filepath))
    if not os.path.isdir(config_json_dir):
        os.makedirs(config_json_dir)
    with open(config_json_filepath, "w", encoding="utf-8") as file:
        file.write(json.dumps(config_dict, indent=4, ensure_ascii=False))
