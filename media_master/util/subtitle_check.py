"""
    subtitle_check.py subtitle check module of media_master
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


