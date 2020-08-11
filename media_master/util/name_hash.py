"""
    name_hash.py name hash module of media_master
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

import hashlib


def hash_name(string: str, output_size_in_byte=3) -> str:
    blake_hash = hashlib.blake2b(
        string.encode("utf-8"), digest_size=output_size_in_byte
    )
    return blake_hash.hexdigest()
