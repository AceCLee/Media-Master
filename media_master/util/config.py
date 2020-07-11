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


def load_config(config_json_filepath):
    if not isinstance(config_json_filepath, str):
        raise TypeError(
            f"type of config_json_filepath must be str "
            f"instead of {type(config_json_filepath)}"
        )
    if not os.path.isfile(config_json_filepath):
        raise FileNotFoundError(
            f"input config file cannot be found with {config_json_filepath}"
        )

    config_data_json = {}
    with open(config_json_filepath, "r", encoding="utf-8") as file:
        data_str = file.read()
        assert data_str, "content of {} is empty!".format(config_json_filepath)
        config_data_json = json.loads(data_str)

    return config_data_json


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
