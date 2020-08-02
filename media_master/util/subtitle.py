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
import copy
import struct

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


def ass_string_style_font_text(string):
    override_block_re_exp: str = "(\\{[^\\{\\}]+?\\})"
    font_name_override_tag_re_exp: str = "\\\\fn(?P<font_name>[^\\\\{\\}]*?)(\\\\|\})"

    override_block_pattern = re.compile(override_block_re_exp)
    font_name_override_tag_pattern = re.compile(font_name_override_tag_re_exp)

    info_dict: dict = dict(original_style_text_set=set(), fn_tag_text_dict={})

    if font_name_override_tag_pattern.search(string):
        split_text_list: list = override_block_pattern.split(string)

        last_fn: str = ""
        for index in range(len(split_text_list)):
            override_block_re_result = override_block_pattern.search(
                split_text_list[index]
            )
            if override_block_re_result:
                font_name_override_tag_re_result = font_name_override_tag_pattern.search(
                    split_text_list[index]
                )
                if font_name_override_tag_re_result:
                    last_fn = font_name_override_tag_re_result.groupdict()[
                        "font_name"
                    ]

            else:
                if last_fn:
                    if last_fn in info_dict["fn_tag_text_dict"].keys():
                        info_dict["fn_tag_text_dict"][last_fn] |= set(
                            split_text_list[index]
                        )
                    else:
                        info_dict["fn_tag_text_dict"][last_fn] = set(
                            split_text_list[index]
                        )
                else:
                    info_dict["original_style_text_set"] |= set(
                        split_text_list[index]
                    )

    else:
        info_dict["original_style_text_set"] = set(
            override_block_pattern.sub("", string)
        )

    return info_dict


def get_missing_glyph_char_set(font_filepath: str, font_index: int, text: str):
    font_file = ttLib.TTFont(font_filepath, fontNumber=font_index)

    text_set: set = set(text)

    used_unicode_char_dict: dict = {}
    for char in text_set:
        char_utf32 = char.encode("utf-32-be")
        unicode_num: int = struct.unpack(">L", char_utf32)[0]
        used_unicode_char_dict[unicode_num] = char

    existed_unicode_set: set = set(font_file.getBestCmap().keys())

    missing_glyph_char_set: set = set()
    for unicode, char in used_unicode_char_dict.items():
        if unicode not in existed_unicode_set:
            missing_glyph_char_set.add(char)

    return missing_glyph_char_set


def get_subtitle_missing_glyph_char_info(
    subtitle_filepath: str,
    allowable_missing_char_set: set = set(),
    input_encoding: str = "utf-8",
    fonts_dir: str = "",
    info_file_dir: str = "font_info",
    info_filename: str = "font_info.json",
):

    subtitle_file = pysubs2.load(subtitle_filepath, encoding=input_encoding)

    style_text_dict: dict = {}
    style_font_text_dict: dict = {}
    fn_font_text_dict: dict = {}

    for event in subtitle_file:
        if event.is_comment:
            continue

        ass_string_style_font_text_dict: dict = ass_string_style_font_text(
            event.text
        )

        if ass_string_style_font_text_dict["original_style_text_set"]:
            if event.style in style_text_dict.keys():
                style_text_dict[
                    event.style
                ] |= ass_string_style_font_text_dict["original_style_text_set"]
            else:
                style_text_dict[event.style] = ass_string_style_font_text_dict[
                    "original_style_text_set"
                ]

        for font in ass_string_style_font_text_dict["fn_tag_text_dict"]:
            if ass_string_style_font_text_dict["fn_tag_text_dict"][font]:
                if font in fn_font_text_dict.keys():
                    fn_font_text_dict[font] |= ass_string_style_font_text_dict[
                        "fn_tag_text_dict"
                    ][font]
                else:
                    fn_font_text_dict[font] = ass_string_style_font_text_dict[
                        "fn_tag_text_dict"
                    ][font]

    for style in style_text_dict.keys():
        if style in subtitle_file.styles.keys():
            font: str = subtitle_file.styles[style].fontname
            if font in style_font_text_dict.keys():
                style_font_text_dict[font] |= style_text_dict[style]
            else:
                style_font_text_dict[font] = style_text_dict[style]
        else:
            raise ValueError
    font_text_dict: dict = copy.copy(style_font_text_dict)

    for fn_font, text_set in fn_font_text_dict.items():
        if fn_font in font_text_dict.keys():
            font_text_dict[fn_font] |= text_set
        else:
            font_text_dict[fn_font] = text_set

    cache_font_text_dict: dict = {}
    for font, text_set in font_text_dict.items():
        if font.strip("@") in cache_font_text_dict.keys():
            cache_font_text_dict[font.strip("@")] |= text_set
        else:
            cache_font_text_dict[font.strip("@")] = text_set
    font_text_dict = cache_font_text_dict

    for font in font_text_dict.keys():
        text_list: list = list(font_text_dict[font])
        text_list.sort()
        font_text_dict[font] = text_list

    font_info_list: list = dir_font_info(
        fonts_dir=fonts_dir,
        info_file_dir=info_file_dir,
        info_filename=info_filename,
    )

    all_font_name_set: set = set()
    all_lower_font_name_set: set = set()
    for font_info in font_info_list:
        for font_name in font_info["family_list"]:
            lower_font_name: str = font_name.lower()
            all_font_name_set.add(font_name)
            all_lower_font_name_set.add(lower_font_name)

    used_font_info_dict: dict = {}
    for font_name in font_text_dict.keys():
        if font_name.lower() not in all_lower_font_name_set:
            raise ValueError(
                f"{font_name} in {subtitle_filepath} does NOT exist!"
            )

        for current_font_info in font_info_list:
            lower_family_list: list = [
                family.lower() for family in current_font_info["family_list"]
            ]
            if font_name.lower() in lower_family_list:
                used_font_info_dict[font_name] = dict(
                    filepath=current_font_info["filepath"],
                    index=current_font_info["index"],
                    file_font_num=current_font_info["file_font_num"],
                )
                break

    missing_glyph_char_info: dict = {}
    for font, current_font_info in used_font_info_dict.items():

        text: str = "".join(font_text_dict[font])

        missing_glyph_char_set: set = get_missing_glyph_char_set(
            font_filepath=current_font_info["filepath"],
            font_index=current_font_info["index"],
            text=text,
        )

        unallowed_missing_glyph_char_set: set = missing_glyph_char_set - allowable_missing_char_set

        if unallowed_missing_glyph_char_set:
            missing_glyph_char_info[font] = unallowed_missing_glyph_char_set

    return missing_glyph_char_info


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


