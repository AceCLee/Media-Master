"""
    check.py checking module of media_master
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


def check_file_environ_path(filename_set: set) -> bool:
    if not isinstance(filename_set, set):
        raise TypeError(
            f"type of filename_set must be set instead of {type(filename_set)}"
        )
    if not all(isinstance(filename, str) for filename in filename_set):
        raise TypeError(
            f"type of all the elements in filename_set must be str"
        )

    path_str: str = os.environ.get("PATH")
    path_dir_set: set = set(path_str.split(";"))
    all_filename_set: set = set()
    for path_dir in path_dir_set:
        all_filename_set |= (
            set(os.listdir(path_dir)) if os.path.isdir(path_dir) else set()
        )
    return all(filename in all_filename_set for filename in filename_set)


