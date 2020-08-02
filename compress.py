"""
    compress.py compress videos with media_master
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
from media_master import transcode_all_missions

# type cmdline to run this script

if __name__ == "__main__":
    config_json_filepath: str = os.path.join(
        os.getcwd(), "data/config/config.json"
    )
    param_template_json_filepath: str = os.path.join(
        os.getcwd(), "data/config/param_template.json"
    )
    global_config_json_filepath: str = os.path.join(
        os.getcwd(), "data/config/global_config.json"
    )

    transcode_all_missions(
        config_json_filepath,
        param_template_json_filepath,
        global_config_json_filepath,
    )
