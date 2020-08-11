"""
    string_util.py string module of media_master
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

import string
import os
from .name_hash import hash_name
from .constant import global_constant


def is_ascii(s) -> str:
    return all(ord(c) < 128 for c in s)


def is_printable(s) -> str:
    printable = set(string.printable)
    return all(c in printable for c in s)


def get_printable(s) -> str:
    printable = set(string.printable)
    return "".join(filter(lambda x: x in printable, s))


def get_unique_printable_filename(filepath: str) -> str:
    if not os.path.isfile(filepath):
        raise ValueError(f"filepath: {filepath} is not a file")
    full_filename: str = os.path.basename(filepath)
    filename, extension = os.path.splitext(full_filename)

    printable_filename: str = get_printable(filename)
    hash_str: str = hash_name(filepath)

    output_filename: str = f"{printable_filename}_{hash_str}"

    return output_filename


def is_filename_with_valid_mark(full_filename: str) -> bool:
    filename, extension = os.path.splitext(full_filename)
    constant = global_constant()
    valid_file_suffix: str = constant.valid_file_suffix
    if filename.endswith(valid_file_suffix):
        return True
    else:
        return False


def get_filename_with_valid_mark(full_filename: str) -> str:
    filename, extension = os.path.splitext(full_filename)
    constant = global_constant()
    output_full_filename: str = filename + constant.valid_file_suffix + extension
    return output_full_filename


