"""
    language.py language module of media_master
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

from iso639 import languages


def all_iso639_code_set():
    all_code_set: set = set()

    all_code_set |= set(la.part1 for la in languages)
    all_code_set |= set(la.part2t for la in languages)
    all_code_set |= set(la.part2b for la in languages)
    all_code_set |= set(la.part3 for la in languages)
    all_code_set |= set(la.part5 for la in languages)

    all_code_set.remove("")

    return all_code_set


