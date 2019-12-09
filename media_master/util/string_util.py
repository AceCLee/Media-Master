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


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def is_printable(s):
    printable = set(string.printable)
    return all(c in printable for c in s)


def get_printable(s):
    printable = set(string.printable)
    return "".join(filter(lambda x: x in printable, s))


