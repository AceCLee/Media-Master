"""
    subtitle.py subtitle module of media_master
    Copyright (C) 2020  Ace C Lee

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

import chardet
import pysubs2
from fontTools import ttLib
from fontTools.ttLib.sfnt import readTTCHeader

from .config import load_config, save_config


def ass_check(subtitle_dir: str, encoding="utf-8-sig"):
    valid_identifier: str = "[Script Info]"
    ass_extension: str = ".ass"
    subtitle_filename_list = []
    for filename in os.listdir(subtitle_dir):
        if filename.endswith(ass_extension):
            subtitle_filename_list.append(filename)
    for filename in subtitle_filename_list:
        filepath = os.path.join(subtitle_dir, filename)
        with open(filepath, mode="r", encoding=encoding) as f:
            text: str = f.read()
            if not text.startswith(valid_identifier):
                print(filename)


def dir_font_info(
    fonts_dir: str = "",
    info_file_dir: str = "font_info",
    info_filename: str = "font_info.json",
):

    available_font_extension_set: set = [
        ".ttf",
        ".ttc",
        ".otf",
        ".woff",
        ".woff2",
    ]

    if not fonts_dir:
        if os.name != "nt":
            raise OSError("only available in Windows")
        windows_fonts_dir: str = os.path.join(
            os.environ["SystemRoot"], "Fonts"
        )
        fonts_dir = windows_fonts_dir

    FONTTOOLS_NAME_ID_FAMILY = 1
    FONTTOOLS_NAME_ID_NAME = 4
    FONTTOOLS_PLATFORM_ID_WINDOWS = 3
    LCID_EN = 1033

    update_font_info_bool: bool = True

    info_file_dir = os.path.abspath(info_file_dir)

    if not os.path.isdir(info_file_dir):
        os.makedirs(info_file_dir)

    info_filepath: str = os.path.join(info_file_dir, info_filename)

    font_info_dict: dict = dict(font_info_list=[])
    if os.path.isfile(info_filepath):
        font_info_dict = load_config(info_filepath)

    all_font_filename_list: list = [
        filename
        for filename in os.listdir(fonts_dir)
        if any(
            filename.lower().endswith(ext)
            for ext in available_font_extension_set
        )
    ]
    all_font_filepath_list: list = [
        os.path.join(fonts_dir, filename)
        for filename in all_font_filename_list
    ]

    info_existed_font_filepath_set: set = set(
        single_font_info_dict["filepath"]
        for single_font_info_dict in font_info_dict["font_info_list"]
    )

    if set(all_font_filepath_list) == info_existed_font_filepath_set:
        update_font_info_bool = False

    if update_font_info_bool:
        font_info_dict = dict(font_info_list=[])
        for font_path in all_font_filepath_list:
            font_num: int = 1
            with open(font_path, "rb") as file:
                if file.read(4) == b"ttcf":
                    font_num = readTTCHeader(file).numFonts

            for font_num_index in range(font_num):
                tt_font = ttLib.TTFont(font_path, fontNumber=font_num_index)
                family_list: list = []
                for name_record in tt_font["name"].names:
                    if (
                        name_record.nameID == FONTTOOLS_NAME_ID_FAMILY
                        and name_record.platformID
                        == FONTTOOLS_PLATFORM_ID_WINDOWS
                    ):
                        record_str: str = ""
                        try:
                            record_str = name_record.toStr()
                        except UnicodeDecodeError:
                            encoding: str = chardet.detect(name_record.string)[
                                "encoding"
                            ]
                            if encoding:
                                record_str = name_record.string.decode(
                                    encoding
                                )
                            else:
                                continue
                        family_list.append(record_str)

                family_list = list(set(family_list))

                single_font_info_dict: dict = dict(
                    filepath=font_path,
                    family_list=family_list,
                    index=font_num_index,
                    file_font_num=font_num,
                )
                font_info_dict["font_info_list"].append(single_font_info_dict)

        save_config(info_filepath, font_info_dict)
    return font_info_dict["font_info_list"]


def get_uninstalled_font_set(
    subtitle_filepath: str, input_encoding="utf-8"
) -> set:
    subs = pysubs2.load(subtitle_filepath, encoding=input_encoding)

    all_style_name_set: set = set(subs.styles.keys())

    used_style_name_set: set = set()
    used_font_name_set: set = set()

    font_name_override_tag_re_exp: str = "\\\\fn(?P<font_name>[^\\\\{\\}]+?)(\\\\|\})"
    line_font_name_override_tag_re_exp: str = "^\\{[^\\{\\}]*?\\\\fn(?P<font_name>[^\\\\{\\}]+?)[^\\{\\}]*?\\}"
    font_name_override_tag_pattern = re.compile(font_name_override_tag_re_exp)
    line_font_name_override_tag_pattern = re.compile(
        line_font_name_override_tag_re_exp
    )

    for event_index in range(len(subs)):
        if subs[event_index].is_comment:
            continue
        re_result = font_name_override_tag_pattern.search(
            subs[event_index].text
        )
        if re_result and line_font_name_override_tag_pattern.search(
            subs[event_index].text
        ):
            all_match_tuple_list = font_name_override_tag_pattern.findall(
                subs[event_index].text
            )
            for match_tuple in all_match_tuple_list:
                used_font_name_set.add(match_tuple[0])
        elif subs[event_index].style in all_style_name_set:
            used_style_name_set.add(subs[event_index].style)

    for style_name in used_style_name_set:
        used_font_name_set.add(subs.styles[style_name].fontname)

    font_info_list: list = dir_font_info(info_file_dir="data/font_info")
    available_font_name_set: set = set()
    for font_info in font_info_list:
        available_font_name_set |= set(font_info["family_list"])

    uninstalled_font_set: set = set(
        font_name
        for font_name in used_font_name_set
        if font_name.strip("@") not in available_font_name_set
    )

    return uninstalled_font_set


def get_vsmod_improper_style(
    subtitle_filepath: str, input_encoding="utf-8"
) -> set:
    subs = pysubs2.load(subtitle_filepath, encoding=input_encoding)

    improper_style_name: str = "default"

    used_style_name_set: set = set()

    line_font_name_override_tag_re_exp: str = "^\\{[^\\{\\}]*?\\\\fn(?P<font_name>[^\\\\{\\}]+?)[^\\{\\}]*?\\}"
    line_font_name_override_tag_pattern = re.compile(
        line_font_name_override_tag_re_exp
    )

    for event_index in range(len(subs)):
        if subs[event_index].is_comment:
            continue
        if not line_font_name_override_tag_pattern.search(
            subs[event_index].text
        ):
            used_style_name_set.add(subs[event_index].style)

    improper_style_set: set = set()

    if improper_style_name in used_style_name_set:
        improper_style_set.add(improper_style_name)

    return improper_style_set


