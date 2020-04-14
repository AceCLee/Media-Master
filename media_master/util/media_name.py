"""
    media_name.py media name module of media_master
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


from pymediainfo import MediaInfo
import os
import re
from .file_hash import hash_file

G_SEP = "_"


def format_string_add(original, new):
    output = ""
    if original:
        output = f"{original}{G_SEP}{new}"
    else:
        output = new
    return output


def add_one_type_media_info_2_format_string(
    format_string, type_str, media_info_list
):
    type_info_list: list = [
        track
        for track in media_info_list
        if track["track_type"].lower() == type_str
    ]

    for type_info in type_info_list:
        format_string = format_string_add(
            format_string, type_info["format"].capitalize()
        )

    return format_string


def merge_repeat(format_string):
    format_name_list = format_string.split(G_SEP)
    unique_format_name_list = list(set(format_name_list))
    unique_format_name_list.sort(key=format_name_list.index)
    new_format_string = ""
    for format_name in unique_format_name_list:
        format_count = format_name_list.count(format_name)
        new_format_name = f"{format_name}x{format_count}"
        new_format_string = format_string_add(
            new_format_string, new_format_name
        )
    return new_format_string


def add_media_info_2_media_name(
    file_dir,
    media_extension_set,
    replace_dict,
    hash_hex_size,
    name_format_reexp="Hevc[^\\[\\]]+",
):
    name_format_pattern = re.compile(name_format_reexp)

    media_filename_list = []
    for full_filename in os.listdir(file_dir):
        filename, extension = os.path.splitext(full_filename)
        if extension in media_extension_set:
            media_filename_list.append(full_filename)

    for full_filename in media_filename_list:
        print(full_filename)
        filename, extension = os.path.splitext(full_filename)

        filepath = os.path.join(file_dir, full_filename)
        media_info_list: list = MediaInfo.parse(filepath).to_data()["tracks"]

        format_string = ""

        format_string = add_one_type_media_info_2_format_string(
            format_string, "video", media_info_list
        )
        format_string = add_one_type_media_info_2_format_string(
            format_string, "audio", media_info_list
        )
        format_string = add_one_type_media_info_2_format_string(
            format_string, "text", media_info_list
        )

        if any(
            track
            for track in media_info_list
            if track["track_type"].lower() == "menu"
        ):
            format_string = format_string_add(format_string, "Menu")

        for key, value in replace_dict.items():
            format_string = format_string.replace(key, value)

        format_string = merge_repeat(format_string)

        output_name = name_format_pattern.sub(
            repl=format_string, string=filename
        )

        if not name_format_pattern.search(filename):
            output_name = f"{filename}[{format_string}]"

        file_hash_value = hash_file(
            filepath=filepath, output_size_in_byte=hash_hex_size
        )

        hash_info = f"[{file_hash_value.upper()}]"

        hash_info_re_exp: str = f"\\[[A-Za-z0-9]+\\]$"

        hash_info_re_result = re.search(hash_info_re_exp, output_name)

        if hash_info_re_result:
            output_name = output_name.replace(hash_info_re_result.group(0), "")

        output_name += hash_info

        output_full_filename = output_name + extension
        print(output_full_filename)
        output_filepath = os.path.join(file_dir, output_full_filename)

        os.rename(filepath, output_filepath)


