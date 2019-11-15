"""
    log.py logging module of media_master
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

import logging
import logging.config


def get_logger(
    log_config_filepath: str, disable_existing_loggers=False
) -> logging.Logger:
    if not log_config_filepath:
        raise ValueError("log_config_filepath is empty")
    logging.config.fileConfig(
        log_config_filepath, disable_existing_loggers=disable_existing_loggers
    )
    logger = logging.getLogger("media_master")

    return logger
