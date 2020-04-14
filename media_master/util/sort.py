"""
    sort.py sort module of media_master
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

from ..error import RangeError
import copy


def resort(src, order_list):
    order_list = copy.deepcopy(order_list)
    if len(order_list) > len(src):
        raise ValueError(
            f"len(order_list) > len(src) {len(order_list)} > {len(src)}"
        )
    if any(index not in order_list for index in range(len(order_list))):
        RangeError(
            message=(
                f"index of src must be in {list(range(len(order_list)))}"
            ),
            valid_range=str(list(range(len(order_list)))),
        )
    if len(order_list) < len(src):
        order_list += list(range(len(order_list), len(src)))
    return sorted(src, key=lambda x: order_list[src.index(x)])


