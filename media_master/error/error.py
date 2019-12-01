"""
    error.py error class of media_master
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


class RangeError(ValueError):
    def __init__(self, message: str, valid_range: str):
        self.message = message
        self.valid_range = valid_range

    def __str__(self):
        return f"\nmessage:{self.message}\nvalid_range:{self.valid_range}"


class MissTemplateError(ValueError):
    def __init__(self, message: str, missing_template: str):
        self.message = message
        self.missing_template = missing_template

    def __str__(self):
        return f"\nmessage:{self.message}\n\
missing_template:{self.missing_template}"


class DirNotFoundError(OSError):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return f"message:{self.message}"

