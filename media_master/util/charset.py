"""
    charset.py charset module of media_master
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

import chardet
from .constant import global_constant
import logging

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


def is_utf8bom(filepath: str) -> bool:
    charset: str = ""
    constant = global_constant()
    python_text_codec_dict: dict = constant.python_text_codec_dict
    with open(filepath, "rb") as file:
        result_dict: dict = chardet.detect(file.read())
        charset = result_dict["encoding"].lower()

    return_bool: bool = False
    if charset == python_text_codec_dict["utf_8_bom"]:
        return_bool = True

    return return_bool


def convert_codec_2_uft8bom(filepath: str):
    charset: str = ""
    constant = global_constant()
    python_text_codec_dict: dict = constant.python_text_codec_dict
    with open(filepath, "rb") as file:
        result_dict: dict = chardet.detect(file.read())
        charset = result_dict["encoding"].lower()

    if charset != python_text_codec_dict["utf_8_bom"]:
        start_info_str: str = (
            f"start to convert codec of {filepath} to utf-8-bom, "
            f"original codec is {charset}"
        )
        g_logger.log(logging.INFO, start_info_str)

        text_str: str = ""
        with open(filepath, "r", encoding=charset) as file:
            text_str = file.read()

        with open(
            filepath, "w", encoding=python_text_codec_dict["utf_8_bom"]
        ) as file:
            file.write(text_str)

        end_info_str: str = (
            f"convert codec of {filepath} to utf-8-bom successfully"
        )
        g_logger.log(logging.INFO, end_info_str)


