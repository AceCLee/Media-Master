"""
    timecode.py time code module of media master
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

import re


def mkv_timecode_2_standard_timecode(mkv_timecode_filepath: str):
    mkv_timecode_comment_re_exp: str = "^# timestamp format v(?P<version_num>\\d+)"
    standard_timecode_comment_format: str = "# timecode format v{version_num}"

    data_str: str = ""
    with open(file=mkv_timecode_filepath, mode="r") as file:
        data_str = file.read()

    re_result = re.search(pattern=mkv_timecode_comment_re_exp, string=data_str)

    if not re_result:
        return mkv_timecode_filepath

    mkv_timecode_comment: str = re_result.group(0)
    version_num: str = re_result.groupdict()["version_num"]
    standard_timecode_comment: str = standard_timecode_comment_format.format(
        version_num=version_num
    )
    data_str = data_str.replace(
        mkv_timecode_comment, standard_timecode_comment
    )

    standard_timecode_filepath: str = mkv_timecode_filepath

    with open(file=standard_timecode_filepath, mode="w") as file:
        file.write(data_str)

    return standard_timecode_filepath


