"""
    transcode.py transcode the whole video
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

import copy
import logging
import os
import re
import shutil
import sys
import threading
import time
import warnings
from collections import namedtuple

from pymediainfo import MediaInfo

from .audio import (
    transcode_audio_opus,
    transcode_audio_qaac,
    transcode_audio_flac,
    transcode_audio_ffmpeg,
)
from .error import RangeError
from .log import get_logger
from .track import AudioTrackFile, MenuTrackFile, TextTrackFile, VideoTrackFile
from .util import (
    convert_chapter_format,
    copy_video,
    extract_all_attachments,
    extract_all_subtitles,
    extract_audio_track,
    extract_chapter,
    extract_video_track,
    get_chapter_format_info_dict,
    get_printable,
    is_printable,
    load_config,
    multiplex_mkv,
    multiplex_mp4,
    remultiplex_ffmpeg,
    resort,
    hash_name,
    get_fr_and_original_fr,
    get_stream_order,
    extract_mkv_video_timecode,
    get_proper_color_specification,
    is_iso_language,
    global_constant,
)
from .video import (
    GopX265VspipeVideoTranscoding,
    NvencVideoTranscoding,
    NvencVspipeVideoTranscoding,
    SegmentedConfigX265VspipeTranscoding,
    X264VspipeVideoTranscoding,
)

g_logger = logging.getLogger(__name__)
g_logger.propagate = True
g_logger.setLevel(logging.DEBUG)


class CompleteVideoTranscoding(object):

    needed_config_key_set: set = {
        "subtitle_filepath_list",
        "frame_server_template_filepath",
        "frame_server_template_config",
        "transcode_audio_bool",
        "audio_transcoding_method",
        "copy_internal_subtitle_bool",
        "copy_chapters_bool",
        "copy_attachments_bool",
        "frame_server",
        "video_transcoding_method",
        "output_full_range_bool",
    }

    max_path_length: int = 255

    def __init__(
        self,
        input_video_filepath: str,
        output_video_dir: str,
        output_video_name: str,
        cache_dir: str,
        config: namedtuple,
    ):
        self._input_video_filepath: str = input_video_filepath
        self._output_video_dir: str = output_video_dir
        self._output_video_filename: str = output_video_name
        self._cache_dir: str = cache_dir
        self._config: namedtuple = config
        if not os.path.isdir(self._cache_dir):
            os.makedirs(self._cache_dir)
        if not os.path.isdir(self._output_video_dir):
            os.makedirs(self._output_video_dir)
        self._remove_filepath_set: set = set()

        self._state_info_dict: dict = {}

        self._state_info_dict["video_stream"] = {}

        self._state_info_dict["video_stream"]["io_complete"] = False

        self._thread_lock = threading.Lock()

        self._cache_media_filename: str = get_printable(
            self._output_video_filename
        ) + f"_{hash_name(self._output_video_filename)}"

        self._pre_multiplex_bool: bool = False

    def copy2new_dir(self, src_filepath: str, output_dir: str):
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        filename: str = os.path.basename(src_filepath)
        output_filepath: str = os.path.join(output_dir, filename)
        shutil.copyfile(src_filepath, output_filepath)
        return output_filepath

    def shorten_inputfile_paths(self):
        for index, external_subtitle_info in enumerate(
            self._config.external_subtitle_info_list
        ):
            filepath: str = external_subtitle_info["filepath"]
            if len(filepath) > self.max_path_length:
                output_filepath: str = self.copy2new_dir(
                    src_filepath=filepath, output_dir=self._cache_dir
                )
                self._config.external_subtitle_info_list[index][
                    "filepath"
                ] = output_filepath
                copy_file_info_str: str = (
                    f"Path of {filepath} is too long, "
                    f"copy {filepath} to {output_filepath}"
                )
                self._remove_filepath_set.add(output_filepath)
                print(copy_file_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, copy_file_info_str)

        for index, external_audio_info in enumerate(
            self._config.external_audio_info_list
        ):
            filepath: str = external_audio_info["filepath"]
            if len(filepath) > self.max_path_length:
                output_filepath: str = self.copy2new_dir(
                    src_filepath=filepath, output_dir=self._cache_dir
                )
                self._config.external_audio_info_list[index][
                    "filepath"
                ] = output_filepath
                copy_file_info_str: str = (
                    f"Path of {filepath} is too long, "
                    f"copy {filepath} to {output_filepath}"
                )
                self._remove_filepath_set.add(output_filepath)
                print(copy_file_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, copy_file_info_str)

        if self._config.external_chapter_info["filepath"]:
            filepath: str = self._config.external_chapter_info["filepath"]
            if len(filepath) > self.max_path_length:
                output_filepath: str = self.copy2new_dir(
                    src_filepath=filepath, output_dir=self._cache_dir
                )
                self._config.external_chapter_info[
                    "filepath"
                ] = output_filepath
                copy_file_info_str: str = (
                    f"Path of {filepath} is too long, "
                    f"copy {filepath} to {output_filepath}"
                )
                self._remove_filepath_set.add(output_filepath)
                print(copy_file_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, copy_file_info_str)

        for index, filepath in enumerate(
            self._config.external_attachment_filepath_list
        ):
            if len(filepath) > self.max_path_length:
                output_filepath: str = self.copy2new_dir(
                    src_filepath=filepath, output_dir=self._cache_dir
                )
                self._config.external_attachment_filepath_list[index][
                    "filepath"
                ] = output_filepath
                copy_file_info_str: str = (
                    f"Path of {filepath} is too long, "
                    f"copy {filepath} to {output_filepath}"
                )
                self._remove_filepath_set.add(output_filepath)
                print(copy_file_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, copy_file_info_str)

        filepath = self._input_video_filepath
        if len(filepath) > self.max_path_length:
            output_filepath: str = self.copy2new_dir(
                src_filepath=filepath, output_dir=self._cache_dir
            )
            self._input_video_filepath = output_filepath
            copy_file_info_str: str = (
                f"Path of {filepath} is too long, "
                f"copy {filepath} to {output_filepath}"
            )
            self._remove_filepath_set.add(output_filepath)
            print(copy_file_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, copy_file_info_str)

    def transcode(self) -> str:
        self.shorten_inputfile_paths()
        self._pre_multiplex(pre_multiplex_filename=self._cache_media_filename)
        thread_bool: bool = self._config.thread_bool
        if thread_bool:
            thread_subtitle = threading.Thread(
                target=self._subtitle_process,
                name="thread_subtitle",
                kwargs=dict(),
            )
            thread_chapter = threading.Thread(
                target=self._chapter_process,
                name="thread_chapter",
                kwargs=dict(),
            )
            thread_attachment = threading.Thread(
                target=self._attachment_process,
                name="thread_attachment",
                kwargs=dict(),
            )
            thread_audio = threading.Thread(
                target=self._audio_process, name="thread_audio", kwargs=dict()
            )
            thread_video_stream = threading.Thread(
                target=self._video_stream_process,
                name="thread_video_stream",
                kwargs=dict(),
            )

            thread_subtitle.start()
            thread_subtitle.join()

            thread_chapter.start()
            thread_chapter.join()

            thread_attachment.start()
            thread_attachment.join()

            thread_video_stream.start()
            while True:
                self._thread_lock.acquire()
                if self._state_info_dict["video_stream"]["io_complete"]:
                    thread_audio.start()
                    self._thread_lock.release()
                    break
                else:
                    self._thread_lock.release()
                    time.sleep(0.5)

            thread_video_stream.join()
            thread_audio.join()
        else:
            self._subtitle_process()
            self._chapter_process()
            self._attachment_process()
            self._audio_process()
            self._video_stream_process()

        self._multiplex_all()
        self._delete_cache_file()

        return self._output_video_filepath

    def _pre_multiplex(self, pre_multiplex_filename: str):
        mkvmerge_unsupported_extension_set: set = {".wmv"}
        mkv_extension: str = ".mkv"

        input_full_filename: str = os.path.basename(self._input_video_filepath)
        filename, extension = os.path.splitext(input_full_filename)

        if extension != mkv_extension:
            pre_muliplex_filename: str = (
                f"{pre_multiplex_filename}" f"_pre_multiplex"
            )
            pre_muliplex_full_filename: str = (
                pre_muliplex_filename + mkv_extension
            )
            pre_muliplex_input_filepath: str = os.path.join(
                self._cache_dir, pre_muliplex_full_filename
            )
            if not os.path.isfile(pre_muliplex_input_filepath):
                input_filepath: str = self._input_video_filepath
                if extension.lower() in mkvmerge_unsupported_extension_set:
                    input_filepath: str = remultiplex_ffmpeg(
                        input_filepath=input_filepath,
                        output_file_dir=self._cache_dir,
                        output_file_name=pre_muliplex_filename + "_ffmpeg",
                        output_file_extension=mkv_extension,
                    )
                    self._remove_filepath_set.add(input_filepath)
                pre_muliplex_input_filepath: str = multiplex_mkv(
                    track_info_list=[
                        dict(filepath=input_filepath, track_id=-1)
                    ],
                    output_file_dir=self._cache_dir,
                    output_file_name=pre_muliplex_filename,
                )
            self._pre_multiplex_bool = True
            self._remove_filepath_set.add(pre_muliplex_input_filepath)
            self._input_video_filepath = pre_muliplex_input_filepath

    def _audio_transcode(
        self, audio_track_file_list: list, filename_suffix=""
    ) -> list:
        transcoded_audio_track_file_list: list = []
        for index, audio_track_file in enumerate(audio_track_file_list):
            transcoded_audio_filename: str = (
                self._cache_media_filename
                + f"{filename_suffix}_audio_index_{index}"
            )
            if self._config.audio_transcoding_method == "opus":
                transcoded_audio_filepath: str = transcode_audio_opus(
                    audio_track_file.filepath,
                    self._cache_dir,
                    transcoded_audio_filename,
                    self._config.audio_transcoding_cmd_param_template,
                )
            elif self._config.audio_transcoding_method == "qaac":
                transcoded_audio_filepath: str = transcode_audio_qaac(
                    audio_track_file.filepath,
                    self._cache_dir,
                    transcoded_audio_filename,
                    self._config.audio_transcoding_cmd_param_template,
                )
            elif self._config.audio_transcoding_method == "flac":
                transcoded_audio_filepath: str = (
                    transcode_audio_flac(
                        input_audio_filepath=audio_track_file.filepath,
                        output_audio_dir=self._cache_dir,
                        output_audio_name=transcoded_audio_filename,
                        flac_exe_cmd_param_template=self._config.audio_transcoding_cmd_param_template,
                    )
                )
            else:
                raise RuntimeError(
                    f"Unsupport transcoding method: "
                    f"{self._config.audio_transcoding_method}"
                )
            self._remove_filepath_set.add(transcoded_audio_filepath)

            transcoded_audio_track_file = copy.deepcopy(audio_track_file)
            transcoded_audio_track_file.filepath = transcoded_audio_filepath
            transcoded_audio_track_file_list.append(
                transcoded_audio_track_file
            )

            if self._config.internal_audio_track_to_process == "default":
                continue
            elif self._config.internal_audio_track_to_process == "all":
                pass
            else:
                raise RuntimeError("It's impossible to execute this code.")

        return transcoded_audio_track_file_list

    def _audio_process(self, delay_sec=0):
        time.sleep(delay_sec)

        internal_audio_process_available_option_set: set = {
            "copy",
            "transcode",
            "skip",
        }
        internal_audio_track_to_process_available_option_set: set = {
            "default",
            "all",
        }
        external_audio_process_available_option_set: set = {
            "copy",
            "transcode",
        }
        audio_prior_available_option_set: set = {"internal", "external"}
        if (
            self._config.internal_audio_process_option
            not in internal_audio_process_available_option_set
        ):
            raise RangeError(
                message=(
                    f"Unknown internal_audio_process_option: "
                    f"{self._config.internal_audio_process_option}"
                ),
                valid_range=str(internal_audio_process_available_option_set),
            )
        if (
            self._config.internal_audio_track_to_process
            not in internal_audio_track_to_process_available_option_set
        ):
            raise RangeError(
                message=(
                    f"Unknown internal_audio_process_option: "
                    f"{self._config.internal_audio_track_to_process}"
                ),
                valid_range=str(
                    internal_audio_track_to_process_available_option_set
                ),
            )
        if (
            self._config.external_audio_process_option
            not in external_audio_process_available_option_set
        ):
            raise RangeError(
                message=(
                    f"Unknown external_audio_process_option: "
                    f"{self._config.external_audio_process_option}"
                ),
                valid_range=str(external_audio_process_available_option_set),
            )

        if (
            self._config.audio_prior_option
            not in audio_prior_available_option_set
        ):
            raise RangeError(
                message=(
                    f"Unknown audio_prior_option: "
                    f"{self._config.audio_prior_option}"
                ),
                valid_range=str(audio_prior_available_option_set),
            )

        internal_audio_track_file_list: list = []
        if self._config.internal_audio_process_option != "skip":
            internal_audio_track_file_list: list = extract_audio_track(
                self._input_video_filepath,
                self._cache_dir,
                self._cache_media_filename,
                audio_track=self._config.internal_audio_track_to_process,
            )
            self._remove_filepath_set |= set(
                audio_track_file.filepath
                for audio_track_file in internal_audio_track_file_list
            )
            for index in range(len(internal_audio_track_file_list)):
                if index < len(self._config.internal_audio_info_list):
                    internal_audio_track_file_list[
                        index
                    ].title = self._config.internal_audio_info_list[index][
                        "title"
                    ]
                    internal_audio_track_file_list[
                        index
                    ].language = self._config.internal_audio_info_list[index][
                        "language"
                    ]
                    internal_audio_track_file_list[
                        index
                    ].delay_ms += self._config.internal_audio_info_list[index][
                        "delay_ms_delta"
                    ]
                else:
                    break

            if self._config.internal_audio_track_order_list:
                internal_audio_track_file_list = resort(
                    src=internal_audio_track_file_list,
                    order_list=copy.deepcopy(
                        self._config.internal_audio_track_order_list
                    ),
                )

        external_audio_track_file_list: list = []
        if self._config.external_audio_info_list:
            for index, external_audio_info in enumerate(
                self._config.external_audio_info_list
            ):
                if external_audio_info["track_index_list"]:
                    current_all_audio_track_file_list: list = (
                        extract_audio_track(
                            input_filepath=external_audio_info["filepath"],
                            output_file_dir=self._cache_dir,
                            output_file_name=self._cache_media_filename
                            + f"_audio_container_index_{index}",
                            audio_track="all",
                        )
                    )

                    for extracted_track in current_all_audio_track_file_list:
                        self._remove_filepath_set.add(extracted_track.filepath)

                    if len(current_all_audio_track_file_list) >= len(
                        external_audio_info["track_index_list"]
                    ):
                        current_all_audio_track_file_list = resort(
                            src=current_all_audio_track_file_list,
                            order_list=copy.deepcopy(
                                external_audio_info["track_index_list"]
                            ),
                        )[: len(external_audio_info["track_index_list"])]

                    for index in range(len(current_all_audio_track_file_list)):
                        current_all_audio_track_file_list[
                            index
                        ].delay_ms = int(
                            external_audio_info["delay_ms"][index]
                        )
                        current_all_audio_track_file_list[
                            index
                        ].title = external_audio_info["title"][index]
                        current_all_audio_track_file_list[
                            index
                        ].language = external_audio_info["language"][index]
                    external_audio_track_file_list.extend(
                        current_all_audio_track_file_list
                    )
                else:
                    audio_info: dict = MediaInfo.parse(
                        external_audio_info["filepath"]
                    ).to_data()["tracks"][1]
                    audio_track_file = AudioTrackFile(
                        filepath=external_audio_info["filepath"],
                        track_index=0,
                        track_format=audio_info["format"].lower(),
                        duration_ms=int(float(audio_info["duration"]))
                        if "duration" in audio_info.keys()
                        else -1,
                        bit_rate_bps=int(audio_info["bit_rate"])
                        if "bit_rate" in audio_info.keys()
                        else -1,
                        bit_depth=int(audio_info["bit_depth"])
                        if "bit_depth" in audio_info.keys()
                        else -1,
                        delay_ms=int(external_audio_info["delay_ms"]),
                        stream_size_byte=int(audio_info["stream_size"])
                        if "stream_size" in audio_info.keys()
                        else -1,
                        title=external_audio_info["title"],
                        language=external_audio_info["language"],
                        default_bool=True if index == 0 else False,
                        forced_bool=False,
                    )
                    external_audio_track_file_list.append(audio_track_file)

        output_internal_audio_track_file_list: list = []
        if not internal_audio_track_file_list:
            pass
        elif self._config.internal_audio_process_option == "transcode":
            output_internal_audio_track_file_list += self._audio_transcode(
                internal_audio_track_file_list, filename_suffix="_internal"
            )
        elif self._config.internal_audio_process_option == "copy":
            output_internal_audio_track_file_list += (
                internal_audio_track_file_list
            )
        elif self._config.internal_audio_process_option == "skip":
            pass
        else:
            raise RuntimeError("It's impossible to execute this code.")

        output_external_audio_track_file_list: list = []
        if external_audio_track_file_list:
            if self._config.external_audio_process_option == "transcode":
                output_external_audio_track_file_list += self._audio_transcode(
                    external_audio_track_file_list, filename_suffix="_external"
                )
            elif self._config.external_audio_process_option == "copy":
                output_external_audio_track_file_list += (
                    external_audio_track_file_list
                )
            else:
                raise RuntimeError("It's impossible to execute this code.")

        self._output_audio_track_file_list: list = []
        if self._config.audio_prior_option == "internal":
            self._output_audio_track_file_list: list = (
                output_internal_audio_track_file_list
                + output_external_audio_track_file_list
            )
        elif self._config.audio_prior_option == "external":
            self._output_audio_track_file_list: list = (
                output_external_audio_track_file_list
                + output_internal_audio_track_file_list
            )
        else:
            raise RuntimeError("It's impossible to execute this code.")

    def _subtitle_process(self):
        subtitle_prior_available_option_set: set = {"internal", "external"}

        if (
            self._config.subtitle_prior_option
            not in subtitle_prior_available_option_set
        ):
            raise RangeError(
                message=(
                    f"Unknown subtitle_prior_option: "
                    f"{self._config.subtitle_prior_option}"
                ),
                valid_range=str(subtitle_prior_available_option_set),
            )

        external_subtitle_info_list: list = copy.deepcopy(
            self._config.external_subtitle_info_list
        )
        external_text_track_file_list: list = []
        for index, external_subtitle_info in enumerate(
            external_subtitle_info_list
        ):
            if external_subtitle_info["track_index_list"]:
                current_all_subtitle_track_file_list: list = (
                    extract_all_subtitles(
                        input_filepath=external_subtitle_info["filepath"],
                        output_file_dir=self._cache_dir,
                        output_file_name=self._cache_media_filename
                        + f"_subtitle_container_index_{index}",
                    )
                )

                for extracted_track in current_all_subtitle_track_file_list:
                    self._remove_filepath_set.add(extracted_track.filepath)

                print(current_all_subtitle_track_file_list)
                print(external_subtitle_info["track_index_list"])

                if len(current_all_subtitle_track_file_list) >= len(
                    external_subtitle_info["track_index_list"]
                ):
                    current_all_subtitle_track_file_list = resort(
                        src=current_all_subtitle_track_file_list,
                        order_list=copy.deepcopy(
                            external_subtitle_info["track_index_list"]
                        ),
                    )[: len(external_subtitle_info["track_index_list"])]

                for index in range(len(current_all_subtitle_track_file_list)):
                    current_all_subtitle_track_file_list[index].delay_ms = int(
                        external_subtitle_info["delay_ms"][index]
                    )
                    current_all_subtitle_track_file_list[
                        index
                    ].title = external_subtitle_info["title"][index]
                    current_all_subtitle_track_file_list[
                        index
                    ].language = external_subtitle_info["language"][index]
                external_text_track_file_list.extend(
                    current_all_subtitle_track_file_list
                )
            else:
                text_track_file = TextTrackFile(
                    filepath=external_subtitle_info["filepath"],
                    track_index=0,
                    track_format=external_subtitle_info["filepath"].split(".")[
                        -1
                    ],
                    duration_ms=-1,
                    bit_rate_bps=-1,
                    delay_ms=external_subtitle_info["delay_ms"],
                    stream_size_byte=-1,
                    title=external_subtitle_info["title"],
                    language=external_subtitle_info["language"],
                    default_bool=True if index == 1 else False,
                    forced_bool=False,
                )
                external_text_track_file_list.append(text_track_file)

        internal_text_track_file_list: list = []
        if self._config.copy_internal_subtitle_bool:
            text_track_file_list: list = copy.deepcopy(
                extract_all_subtitles(
                    self._input_video_filepath,
                    self._cache_dir,
                    self._cache_media_filename,
                )
            )
            for index in range(len(text_track_file_list)):
                self._remove_filepath_set.add(
                    text_track_file_list[index].filepath
                )
                if index < len(self._config.internal_subtitle_info_list):
                    text_track_file_list[
                        index
                    ].title = self._config.internal_subtitle_info_list[index][
                        "title"
                    ]
                    text_track_file_list[
                        index
                    ].language = self._config.internal_subtitle_info_list[
                        index
                    ][
                        "language"
                    ]

            if self._config.internal_subtitle_track_order_list:
                text_track_file_list = resort(
                    src=text_track_file_list,
                    order_list=copy.deepcopy(
                        self._config.internal_subtitle_track_order_list
                    ),
                )

            internal_text_track_file_list += text_track_file_list

        self._output_text_track_file_list: list = []
        if self._config.subtitle_prior_option == "internal":
            self._output_text_track_file_list: list = (
                internal_text_track_file_list + external_text_track_file_list
            )
        elif self._config.subtitle_prior_option == "external":
            self._output_text_track_file_list: list = (
                external_text_track_file_list + internal_text_track_file_list
            )
        else:
            raise RuntimeError("It's impossible to execute this code.")

    def _chapter_process(self):
        all_chapter_format_info_dict: dict = get_chapter_format_info_dict()
        if self._config.package_format == "mkv":
            dst_chapter_format = "matroska"
        elif self._config.package_format == "mp4":
            dst_chapter_format = "ogm"
        else:
            raise ValueError

        chapter_extension_set: set = set(
            chapter_format_dict["ext"]
            for chapter_format_dict in all_chapter_format_info_dict.values()
        )

        if self._config.external_chapter_info["filepath"]:
            if any(
                self._config.external_chapter_info["filepath"].endswith(
                    chapter_extension
                )
                for chapter_extension in chapter_extension_set
            ):
                dst_chapter_filepath: str = convert_chapter_format(
                    src_chapter_filepath=self._config.external_chapter_info[
                        "filepath"
                    ],
                    output_dir=self._cache_dir,
                    dst_chapter_format=dst_chapter_format,
                )
                self._menu_track_file = MenuTrackFile(
                    filepath=dst_chapter_filepath
                )
            else:
                self._menu_track_file = extract_chapter(
                    self._config.external_chapter_info["filepath"],
                    self._cache_dir,
                    self._cache_media_filename,
                    chapter_format=dst_chapter_filepath,
                )
                if self._menu_track_file is None:
                    raise RuntimeError(
                        f"There are no chapter info in "
                        f"{self._config.external_chapter_info['filepath']}"
                    )
        elif self._config.copy_internal_chapter_bool:
            self._menu_track_file = extract_chapter(
                self._input_video_filepath,
                self._cache_dir,
                self._cache_media_filename,
                chapter_format=dst_chapter_format,
            )
            if self._menu_track_file is None:
                self._menu_track_file = MenuTrackFile(filepath="")

    def _attachment_process(self):
        self._attachments_filepath_set = set()
        if self._config.copy_internal_attachment_bool:
            self._attachments_filepath_set |= set(
                extract_all_attachments(
                    self._input_video_filepath, self._cache_file_dir
                )
            )
            self._remove_filepath_set |= self._attachments_filepath_set
        if self._config.external_attachment_filepath_list:
            self._attachments_filepath_set |= set(
                self._config.external_attachment_filepath_list
            )

    def _video_stream_process(self):
        self._thread_lock.acquire()
        self._state_info_dict["video_stream"]["io_complete"] = True
        self._thread_lock.release()

        self._video_timecode_filepath: str = ""
        self._first_multiplex_mkv_bool: bool = False

        if self._config.video_process_option == "copy":
            if self._config.package_format == "mp4":
                self._video_track_file = extract_video_track(
                    input_filepath=self._input_video_filepath,
                    output_file_dir=self._cache_dir,
                    output_file_name=self._cache_media_filename,
                )
                if self._video_track_file.frame_rate_mode == "vfr":
                    self._video_timecode_filepath = extract_mkv_video_timecode(
                        filepath=self._input_video_filepath,
                        output_dir=self._cache_dir,
                        output_name=self._cache_media_filename,
                    )
                    self._first_multiplex_mkv_bool = True
                self._remove_filepath_set.add(self._video_track_file.filepath)
            else:
                media_info_list: list = MediaInfo.parse(
                    self._input_video_filepath
                ).to_data()["tracks"]
                video_info_dict: dict = next(
                    (
                        track
                        for track in media_info_list
                        if track["track_type"] == "Video"
                    ),
                    None,
                )
                frame_rate_info_dict: dict = get_fr_and_original_fr(
                    video_info_dict
                )

                color_specification_dict: dict = (
                    get_proper_color_specification(video_info_dict)
                )

                self._video_track_file: VideoTrackFile = VideoTrackFile(
                    filepath=self._input_video_filepath,
                    track_index=get_stream_order(
                        video_info_dict["streamorder"]
                    ),
                    track_format=video_info_dict["format"].lower(),
                    duration_ms=int(float(video_info_dict["duration"])),
                    bit_rate_bps=int(video_info_dict["bit_rate"])
                    if "bit_rate" in video_info_dict.keys()
                    else -1,
                    width=video_info_dict["width"],
                    height=video_info_dict["height"],
                    frame_rate_mode=video_info_dict["frame_rate_mode"].lower(),
                    frame_rate=frame_rate_info_dict["frame_rate"],
                    original_frame_rate=frame_rate_info_dict[
                        "original_frame_rate"
                    ],
                    frame_count=int(video_info_dict["frame_count"]),
                    color_range=video_info_dict["color_range"].lower()
                    if "color_range" in video_info_dict.keys()
                    else "limited",
                    color_space=video_info_dict["color_space"]
                    if "color_space" in video_info_dict.keys()
                    else "",
                    color_matrix=color_specification_dict["color_matrix"],
                    color_primaries=color_specification_dict[
                        "color_primaries"
                    ],
                    transfer=color_specification_dict["transfer"],
                    chroma_subsampling=video_info_dict["chroma_subsampling"]
                    if "chroma_subsampling" in video_info_dict.keys()
                    else "",
                    bit_depth=int(video_info_dict["bit_depth"])
                    if "bit_depth" in video_info_dict.keys()
                    else -1,
                    sample_aspect_ratio=video_info_dict["pixel_aspect_ratio"]
                    if "pixel_aspect_ratio" in video_info_dict.keys()
                    else 1,
                    delay_ms=int(float(video_info_dict["delay"]))
                    if "delay" in video_info_dict.keys()
                    else 0,
                    stream_size_byte=int(video_info_dict["stream_size"])
                    if "stream_size" in video_info_dict.keys()
                    else -1,
                    title=video_info_dict["title"]
                    if "title" in video_info_dict.keys()
                    else "",
                    language=video_info_dict["language"]
                    if "language" in video_info_dict.keys()
                    else "",
                    default_bool=True
                    if "default" not in video_info_dict.keys()
                    else (
                        True
                        if video_info_dict["default"].lower() == "yes"
                        else False
                    ),
                    forced_bool=True
                    if "forced" not in video_info_dict.keys()
                    else (
                        True
                        if video_info_dict["forced"].lower() == "yes"
                        else False
                    ),
                )

            self._output_video_track_file = self._video_track_file

        elif self._config.video_process_option == "transcode":
            self._video_track_file = copy_video(
                input_filepath=self._input_video_filepath,
                output_file_dir=self._cache_dir,
                output_file_name=self._cache_media_filename,
                using_original_if_possible=self._pre_multiplex_bool,
            )

            if self._video_track_file.filepath != self._input_video_filepath:
                self._remove_filepath_set.add(self._video_track_file.filepath)

            output_frame_rate_mode: str = self._config.output_frame_rate_mode
            if (
                output_frame_rate_mode == ""
                or output_frame_rate_mode == "auto"
            ):
                output_frame_rate_mode = self._video_track_file.frame_rate_mode

            if output_frame_rate_mode == "unchange":
                output_frame_rate_mode = self._video_track_file.frame_rate_mode

            if output_frame_rate_mode == "vfr":
                if self._video_track_file.frame_rate_mode == "cfr":
                    raise ValueError(
                        f"input video of cfr only support cfr output."
                    )
                if self._config.package_format == "mp4":
                    self._first_multiplex_mkv_bool = True
                if (
                    self._video_track_file.frame_rate_mode == "vfr"
                    and self._config.output_fps
                ):
                    raise ValueError(
                        "if input video is vfr video and "
                        "output video is vfr video, "
                        "changing fps is not supported."
                    )

            if output_frame_rate_mode == "vfr":
                self._video_timecode_filepath = extract_mkv_video_timecode(
                    filepath=self._input_video_filepath,
                    output_dir=self._cache_dir,
                    output_name=self._cache_media_filename,
                )

            output_dynamic_range_mode: str = ""
            if (
                self._config.output_dynamic_range_mode == ""
                or self._config.output_dynamic_range_mode == "unchange"
            ):
                output_dynamic_range_mode = (
                    "sdr" if not self._video_track_file.hdr_bool else "hdr"
                )
            elif self._config.output_dynamic_range_mode == "hdr":
                if not self._video_track_file.hdr_bool:
                    raise ValueError("sdr to hdr is not supported.")
                output_dynamic_range_mode = (
                    self._config.output_dynamic_range_mode
                )
            elif self._config.output_dynamic_range_mode == "hdr":
                output_dynamic_range_mode = (
                    self._config.output_dynamic_range_mode
                )
            else:
                raise ValueError(
                    f"unknown output_dynamic_range_mode: "
                    f"{self._config.output_dynamic_range_mode}"
                )

            if (
                output_dynamic_range_mode == "hdr"
                and self._config.video_transcoding_method == "x264"
            ):
                raise ValueError(f"avc does not support hdr")

            other_config: dict = dict(
                frame_rate_mode=self._video_track_file.frame_rate_mode,
                frame_rate=self._video_track_file.frame_rate,
                original_frame_rate=self._video_track_file.original_frame_rate,
                input_sar=self._video_track_file.sample_aspect_ratio,
                output_sar=self._config.output_sar,
                input_full_range_bool=True
                if self._video_track_file.color_range == "full"
                else False,
                output_full_range_bool=self._config.output_full_range_bool,
                input_video_width=self._video_track_file.width,
                input_video_height=self._video_track_file.height,
                input_color_matrix=self._video_track_file.color_matrix,
                input_color_primaries=self._video_track_file.color_primaries,
                input_transfer=self._video_track_file.transfer,
                total_frame_cnt=self._video_track_file.frame_count,
                video_transcoding_cmd_param_template_config=(
                    self._config.video_transcoding_cmd_param_template_config
                ),
                output_fps=self._config.output_fps,
                output_frame_rate_mode=output_frame_rate_mode,
                video_timecode_filepath=self._video_timecode_filepath,
                output_dynamic_range_mode=output_dynamic_range_mode,
                input_hdr_bool=self._video_track_file.hdr_bool,
                input_mastering_display_color_primaries=self._video_track_file.mastering_display_color_primaries,
                input_min_mastering_display_luminance=self._video_track_file.min_mastering_display_luminance,
                input_max_mastering_display_luminance=self._video_track_file.max_mastering_display_luminance,
                input_max_content_light_level=self._video_track_file.max_content_light_level,
                input_max_frameaverage_light_level=self._video_track_file.max_frameaverage_light_level,
            )

            if self._config.frame_server == "vspipe":
                if self._config.video_transcoding_method == "x265":
                    if self._config.segmented_transcode_config_list:
                        x265_transcoding_mission = SegmentedConfigX265VspipeTranscoding(
                            input_video_filepath=self._video_track_file.filepath,
                            frame_server_template_filepath=self._config.frame_server_template_filepath,
                            frame_server_script_cache_dir=self._cache_dir,
                            frame_server_script_filename=self._cache_media_filename,
                            frame_server_template_config=copy.deepcopy(
                                self._config.frame_server_template_config
                            ),
                            output_video_dir=self._cache_dir,
                            output_video_filename=self._cache_media_filename,
                            transcoding_cmd_param_template=copy.deepcopy(
                                self._config.video_transcoding_cmd_param_template
                            ),
                            other_config=copy.deepcopy(other_config),
                            gop_frame_cnt=self._config.gop_segmented_transcode_config[
                                "gop_frame_cnt"
                            ],
                            first_frame_index=0,
                            last_frame_index=self._video_track_file.frame_count
                            - 1,
                            segmented_transcode_config_list=self._config.segmented_transcode_config_list,
                        )
                    else:
                        x265_transcoding_mission = GopX265VspipeVideoTranscoding(
                            input_video_filepath=self._video_track_file.filepath,
                            frame_server_template_filepath=self._config.frame_server_template_filepath,
                            frame_server_script_cache_dir=self._cache_dir,
                            frame_server_script_filename=self._cache_media_filename,
                            frame_server_template_config=copy.deepcopy(
                                self._config.frame_server_template_config
                            ),
                            output_video_dir=self._cache_dir,
                            output_video_filename=self._cache_media_filename,
                            transcoding_cmd_param_template=copy.deepcopy(
                                self._config.video_transcoding_cmd_param_template
                            ),
                            other_config=copy.deepcopy(other_config),
                            gop_frame_cnt=self._config.gop_segmented_transcode_config[
                                "gop_frame_cnt"
                            ],
                            first_frame_index=0,
                            last_frame_index=self._video_track_file.frame_count
                            - 1,
                        )
                    result = x265_transcoding_mission.transcode()
                    compressed_video_cache_filepath: str = result
                elif self._config.video_transcoding_method == "x264":
                    x264_transcoding_mission = X264VspipeVideoTranscoding(
                        self._video_track_file.filepath,
                        self._config.frame_server_template_filepath,
                        self._cache_dir,
                        self._cache_media_filename,
                        copy.deepcopy(
                            self._config.frame_server_template_config
                        ),
                        self._cache_dir,
                        self._cache_media_filename,
                        copy.deepcopy(
                            self._config.video_transcoding_cmd_param_template
                        ),
                        copy.deepcopy(other_config),
                    )
                    result_tuple: tuple = x264_transcoding_mission.transcode()
                    compressed_video_cache_filepath: str = result_tuple[0]
                    self._encode_fps = result_tuple[1]
                    self._encode_bitrate = result_tuple[2]
                elif self._config.video_transcoding_method == "nvenc":
                    nvenc_transcoding_mission = NvencVspipeVideoTranscoding(
                        input_video_filepath=self._video_track_file.filepath,
                        frame_server_template_filepath=self._config.frame_server_template_filepath,
                        frame_server_script_cache_dir=self._cache_dir,
                        frame_server_script_filename=self._cache_media_filename,
                        frame_server_template_config=copy.deepcopy(
                            self._config.frame_server_template_config
                        ),
                        output_video_dir=self._cache_dir,
                        output_video_filename=self._cache_media_filename,
                        transcoding_cmd_param_template=copy.deepcopy(
                            self._config.video_transcoding_cmd_param_template
                        ),
                        other_config=copy.deepcopy(other_config),
                    )
                    compressed_video_cache_filepath: str = (
                        nvenc_transcoding_mission.transcode()
                    )
                else:
                    raise RangeError(
                        message=(
                            f"Unknown video_transcoding_method with vspipe: "
                            f"{self._config.video_transcoding_method}"
                        ),
                        valid_range=str({"x265", "x264", "nvenc"}),
                    )
            elif self._config.frame_server == "":
                if self._config.video_transcoding_method == "nvenc":
                    nvenc_transcoding_mission = NvencVideoTranscoding(
                        input_video_filepath=self._video_track_file.filepath,
                        output_video_dir=self._cache_dir,
                        output_video_filename=self._cache_media_filename,
                        transcoding_cmd_param_template=copy.deepcopy(
                            self._config.video_transcoding_cmd_param_template
                        ),
                        other_config=copy.deepcopy(other_config),
                    )
                    compressed_video_cache_filepath: str = (
                        nvenc_transcoding_mission.transcode()
                    )
                else:
                    raise RangeError(
                        message=(
                            f"Unknown video_transcoding_method "
                            f"without frameserver: "
                            f"{self._config.video_transcoding_method}"
                        ),
                        valid_range=str({"nvenc"}),
                    )
            else:
                raise RangeError(
                    message=(
                        f"Unknown frameserver: {self._config.frame_server}"
                    ),
                    valid_range=str({"vspipe", ""}),
                )
            media_info_list: list = MediaInfo.parse(
                compressed_video_cache_filepath
            ).to_data()["tracks"]
            video_info_dict: dict = next(
                (
                    track
                    for track in media_info_list
                    if track["track_type"] == "Video"
                ),
                None,
            )
            
            
            
            
            
            
            
            
            
            
            
            
            

            self._output_video_track_file = copy.deepcopy(
                self._video_track_file
            )
            self._output_video_track_file.filepath = (
                compressed_video_cache_filepath
            )
            self._remove_filepath_set.add(compressed_video_cache_filepath)

        self._output_video_track_file.color_range = (
            "full" if self._config.output_full_range_bool else "limited"
        )
        self._output_video_track_file.title = self._config.video_title
        self._output_video_track_file.language = self._config.video_language

    def _multiplex_all(self):
        track_info_list: list = [
            dict(
                filepath=self._output_video_track_file.filepath,
                delay_ms=self._output_video_track_file.delay_ms,
                track_type=self._output_video_track_file.track_type,
                track_name=self._output_video_track_file.title,
                language=self._output_video_track_file.language,
                track_id=self._output_video_track_file.track_index,
                timecode_filepath=self._video_timecode_filepath,
            )
        ]
        track_info_list += [
            dict(
                filepath=audio_track_file.filepath,
                delay_ms=audio_track_file.delay_ms,
                track_type=audio_track_file.track_type,
                track_name=audio_track_file.title,
                language=audio_track_file.language,
                track_id=audio_track_file.track_index,
                timecode_filepath="",
            )
            for audio_track_file in self._output_audio_track_file_list
        ]

        track_info_list += [
            dict(
                filepath=text_track_file.filepath,
                delay_ms=text_track_file.delay_ms,
                track_type="subtitle",
                track_name=text_track_file.title,
                language=text_track_file.language,
                track_id=0,
                timecode_filepath="",
            )
            for text_track_file in self._output_text_track_file_list
        ]

        if self._config.package_format == "mkv":
            self._output_video_filepath: str = multiplex_mkv(
                track_info_list=copy.deepcopy(track_info_list),
                output_file_dir=self._output_video_dir,
                output_file_name=self._output_video_filename,
                chapters_filepath=self._menu_track_file.filepath,
                attachments_filepath_set=self._attachments_filepath_set,
            )
        elif self._config.package_format == "mp4":
            if self._first_multiplex_mkv_bool:
                cache_mkv_output_video_filepath: str = multiplex_mkv(
                    track_info_list=copy.deepcopy(track_info_list),
                    output_file_dir=self._cache_dir,
                    output_file_name=self._output_video_filename,
                    chapters_filepath=self._menu_track_file.filepath,
                    attachments_filepath_set=self._attachments_filepath_set,
                )
                self._remove_filepath_set.add(cache_mkv_output_video_filepath)
                self._output_video_filepath: str = remultiplex_ffmpeg(
                    input_filepath=cache_mkv_output_video_filepath,
                    output_file_dir=self._output_video_dir,
                    output_file_name=self._output_video_filename,
                    output_file_extension=".mp4",
                )
            else:
                self._output_video_filepath: str = multiplex_mp4(
                    track_info_list=copy.deepcopy(track_info_list),
                    output_file_dir=self._output_video_dir,
                    output_file_name=self._output_video_filename,
                    chapters_filepath=self._menu_track_file.filepath,
                )
        else:
            raise RangeError(
                message=(
                    f"Unknown package_format: "
                    f"{self._config.package_format}"
                ),
                valid_range=str({"mkv", "mp4"}),
            )

    def _delete_cache_file(self):
        
        origin_video_cache_filename: str = os.path.basename(
            self._video_track_file.filepath
        )
        for filename in set(os.listdir(self._cache_dir)):
            if (
                origin_video_cache_filename in filename
                and filename != origin_video_cache_filename
            ):
                self._remove_filepath_set.add(
                    os.path.join(self._cache_dir, filename)
                )

        for filepath in self._remove_filepath_set:
            if os.path.isfile(filepath):
                delete_info_str: str = f"transcode: delete {filepath}"
                print(delete_info_str, file=sys.stderr)
                g_logger.log(logging.INFO, delete_info_str)
                os.remove(filepath)


class SeriesVideoTranscoding(object):

    needed_config_key_set: set = {
        "frame_server_template_filepath",
        "frame_server_template_config",
        "transcode_audio_bool",
        "audio_transcoding_method",
        "copy_internal_subtitle_bool",
        "copy_chapters_bool",
        "copy_attachments_bool",
        "frame_server",
        "video_transcoding_method",
        "output_full_range_bool",
    }

    def __init__(
        self,
        input_video_dir: str,
        input_video_filename_reexp: str,
        external_subtitle_info_list: list,
        output_video_dir: str,
        output_video_name_template_str: str,
        cache_dir: str,
        episode_list: list,
        config: namedtuple,
    ):
        self._input_video_dir: str = input_video_dir
        self._input_video_filename_reexp: str = input_video_filename_reexp
        self._external_subtitle_info_list: list = copy.deepcopy(
            external_subtitle_info_list
        )
        self._output_video_dir: str = output_video_dir
        self._output_video_name_template_str: str = (
            output_video_name_template_str
        )
        self._cache_dir: str = cache_dir
        self._episode_list: list = copy.deepcopy(episode_list)
        self._config: namedtuple = copy.deepcopy(config)

        if not os.path.isdir(self._cache_dir):
            os.makedirs(self._cache_dir)
        if not os.path.isdir(self._output_video_dir):
            os.makedirs(self._output_video_dir)

    def transcode(self):
        video_info: dict = {}
        for filename in os.listdir(self._input_video_dir):
            re_result = re.search(
                pattern=self._input_video_filename_reexp, string=filename
            )
            if re_result:
                episode: str = str(int(re_result.group(1)))
                if episode in video_info.keys():
                    raise RuntimeError(
                        f"repetitive episode {episode} in {self._input_video_dir}"
                    )
                video_info[episode] = dict(
                    filepath=os.path.join(self._input_video_dir, filename)
                )
        if not video_info:
            raise RuntimeError(
                f"Can not match any one video with "
                f"{self._input_video_filename_reexp} "
                f"in {self._input_video_dir}"
            )
        subtitle_info_list: list = []
        for external_subtitle_info in self._config.external_subtitle_info_list:
            subtitle_info: dict = {}
            for filename in os.listdir(external_subtitle_info["subtitle_dir"]):
                re_result = re.search(
                    pattern=external_subtitle_info["subtitle_filename_reexp"],
                    string=filename,
                )
                if re_result:
                    episode: str = re_result.group(1)
                    if episode in subtitle_info.keys():
                        raise RuntimeError(
                            f"repetitive episode in \
{external_subtitle_info['subtitle_dir']}"
                        )
                    subtitle_info[str(int(episode))] = dict(
                        filepath=os.path.join(
                            external_subtitle_info["subtitle_dir"], filename
                        ),
                        title=external_subtitle_info["title"],
                        language=external_subtitle_info["language"],
                        delay_ms=external_subtitle_info["delay_ms"][episode]
                        if episode in external_subtitle_info["delay_ms"].keys()
                        else (
                            0
                            if not external_subtitle_info["track_index_list"]
                            else [
                                0
                                for i in range(
                                    len(
                                        external_subtitle_info[
                                            "track_index_list"
                                        ]
                                    )
                                )
                            ]
                        ),
                        track_index_list=external_subtitle_info[
                            "track_index_list"
                        ],
                    )

            if not subtitle_info:
                raise RuntimeError(
                    f"Can not match any one subtitle with "
                    f"{external_subtitle_info['subtitle_filename_reexp']} "
                    f"in {external_subtitle_info['subtitle_dir']}"
                )

            subtitle_info_list.append(subtitle_info)
        audio_info_list: list = []
        for external_audio_info in self._config.external_audio_info_list:
            audio_info: dict = {}
            for filename in os.listdir(external_audio_info["audio_dir"]):
                re_result = re.search(
                    pattern=external_audio_info["audio_filename_reexp"],
                    string=filename,
                )
                if re_result:
                    episode: str = re_result.group(1)
                    if episode in audio_info.keys():
                        raise RuntimeError(
                            f"repetitive episode in"
                            f"{external_audio_info['audio_dir']}"
                        )
                    audio_info[str(int(episode))] = dict(
                        filepath=os.path.join(
                            external_audio_info["audio_dir"], filename
                        ),
                        title=external_audio_info["title"],
                        language=external_audio_info["language"],
                        delay_ms=external_audio_info["delay_ms"][episode]
                        if episode in external_audio_info["delay_ms"].keys()
                        else (
                            0
                            if not external_audio_info["track_index_list"]
                            else [
                                0
                                for i in range(
                                    len(
                                        external_audio_info["track_index_list"]
                                    )
                                )
                            ]
                        ),
                        track_index_list=external_audio_info[
                            "track_index_list"
                        ],
                    )

            if not audio_info:
                raise RuntimeError(
                    f"Can not match any one audio with "
                    f"{external_audio_info['audio_filename_reexp']} "
                    f"in {external_audio_info['audio_dir']}"
                )
            audio_info_list.append(audio_info)
        chapter_info: dict = {}
        if (
            self._config.external_chapter_info["chapter_dir"]
            and self._config.external_chapter_info["chapter_filename_reexp"]
        ):
            for filename in os.listdir(
                self._config.external_chapter_info["chapter_dir"]
            ):
                re_result = re.search(
                    pattern=self._config.external_chapter_info[
                        "chapter_filename_reexp"
                    ],
                    string=filename,
                )
                if re_result:
                    episode: str = re_result.group(1)
                    if episode in chapter_info.keys():
                        raise RuntimeError(
                            f"repetitive episode in "
                            f"{self._config.external_chapter_info['chapter_dir']}"
                        )
                    chapter_info[str(int(episode))] = dict(
                        filepath=os.path.join(
                            self._config.external_chapter_info["chapter_dir"],
                            filename,
                        )
                    )
            if not chapter_info:
                raise RuntimeError(
                    f"Can not match any one chapter with "
                    f"{self._config.external_chapter_info['chapter_filename_reexp']} "
                    f"in {self._config.external_chapter_info['chapter_dir']}"
                )

        def length_check(info_list, video_info):
            length_list: list = []
            length_list.append(len(video_info))
            length_list += [len(info) for info in info_list]
            if max(length_list) != min(length_list):
                video_filename_list: list = [
                    os.path.basename(one_video_info["filepath"])
                    for one_video_info in video_info.values()
                ]
                warning_str: str = f"{video_filename_list} {len(video_info)}"
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)
                for info in info_list:
                    filename_list: list = [
                        os.path.basename(one_info["filepath"])
                        for one_info in info.values()
                    ]
                    warning_str: str = (f"{filename_list} {len(info)}")
                    g_logger.log(logging.WARNING, warning_str)
                    warnings.warn(warning_str, RuntimeWarning)
                warning_str: str = (
                    f"max episode length is {max(length_list)}, "
                    f"min episode length is {min(length_list)}"
                )
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)
        if self._config.external_subtitle_info_list:
            length_check(subtitle_info_list, video_info)

        if self._config.external_audio_info_list:
            length_check(audio_info_list, video_info)

        video_filename_list: list = [
            os.path.basename(one_video_info["filepath"])
            for one_video_info in video_info.values()
        ]
        transcode_series_video_debug_str: str = (
            f"transcode series: videos:{video_filename_list}"
        )
        g_logger.log(logging.DEBUG, transcode_series_video_debug_str)

        for index, subtitle_info in enumerate(subtitle_info_list):
            subtitle_filename_list: list = [
                os.path.basename(one_subtitle_info["filepath"])
                for one_subtitle_info in subtitle_info.values()
            ]
            transcode_series_subtitle_debug_str: str = (
                f"transcode series:"
                f"subtitles {index}:{subtitle_filename_list}"
            )
            g_logger.log(logging.DEBUG, transcode_series_subtitle_debug_str)

        if (
            self._config.external_chapter_info["chapter_dir"]
            and self._config.external_chapter_info["chapter_filename_reexp"]
        ):
            length_list: list = []
            length_list.append(len(video_info))
            length_list += [
                len(subtitle_info) for subtitle_info in subtitle_info_list
            ]
            if len(video_info) != len(chapter_info):
                raise RuntimeError(f"len(video_info) != len(chapter_info)")

        start_info_str: str = (
            f"transcode series: starting transcoding "
            f"{self._input_video_dir}"
        )
        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)

        for index, subtitle_info in enumerate(subtitle_info_list):
            if any(
                str(int(episode_num)) not in subtitle_info.keys()
                for episode_num in self._episode_list
            ):
                warning_str: str = (
                    f"transcode series: "
                    f"{self._episode_list} mismatch subtitles in "
                    f"{self._config.external_subtitle_info_list[index]['subtitle_filename_reexp']}"
                )
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)

        for index, audio_info in enumerate(audio_info_list):
            if any(
                str(int(episode_num)) not in audio_info.keys()
                for episode_num in self._episode_list
            ):
                warning_str: str = (
                    f"transcode series: "
                    f"{self._episode_list} mismatch audios in "
                    f"{self._config.external_audio_info_list[index]['audio_filename_reexp']}"
                )
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)

        if len(video_info) < len(self._episode_list):
            raise ValueError(
                f"len(video_info) < len(self._episode_list) "
                f"{len(video_info)} < {len(self._episode_list)}"
            )
        for episode_num in self._episode_list:
            video_filepath: str = video_info[str(episode_num)]["filepath"]
            output_video_filename: str = (
                self._output_video_name_template_str.format(
                    episode=episode_num
                )
            )

            config: dict = self._config._asdict()
            config.pop("input_video_dir")
            config.pop("input_video_filename_reexp")
            config.pop("output_video_dir")
            config.pop("output_video_name_template_str")
            config.pop("episode_list")
            config["external_subtitle_info_list"] = [
                dict(
                    filepath=subtitle_info[str(int(episode_num))]["filepath"],
                    title=subtitle_info[str(int(episode_num))]["title"],
                    language=subtitle_info[str(int(episode_num))]["language"],
                    delay_ms=subtitle_info[str(int(episode_num))]["delay_ms"],
                    track_index_list=subtitle_info[str(int(episode_num))][
                        "track_index_list"
                    ],
                )
                for subtitle_info in subtitle_info_list
                if str(int(episode_num)) in subtitle_info.keys()
            ]
            config["external_audio_info_list"] = [
                dict(
                    filepath=audio_info[str(int(episode_num))]["filepath"],
                    title=audio_info[str(int(episode_num))]["title"],
                    language=audio_info[str(int(episode_num))]["language"],
                    delay_ms=audio_info[str(int(episode_num))]["delay_ms"],
                    track_index_list=audio_info[str(int(episode_num))][
                        "track_index_list"
                    ],
                )
                for audio_info in audio_info_list
                if str(int(episode_num)) in audio_info.keys()
            ]
            config["external_chapter_info"] = (
                chapter_info[str(int(episode_num))]
                if chapter_info
                else dict(filepath="")
            )

            config["segmented_transcode_config_list"] = (
                config["segmented_transcode_config"][str(int(episode_num))]
                if str(int(episode_num))
                in config["segmented_transcode_config"].keys()
                else []
            )

            Config: namedtuple = namedtuple("Config", sorted(config))
            config: namedtuple = Config(**config)

            start_info_str: str = (
                f"transcode series: starting "
                f"transcoding episode {episode_num}"
            )
            print(start_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, start_info_str)

            current_episode_transcoding = CompleteVideoTranscoding(
                input_video_filepath=video_filepath,
                output_video_dir=self._output_video_dir,
                output_video_name=output_video_filename,
                cache_dir=self._cache_dir,
                config=copy.deepcopy(config),
            )
            output_video_filepath: str = (
                current_episode_transcoding.transcode()
            )

            end_info_str: str = (
                f"transcode series: "
                f"transcoding episode {episode_num} to "
                f"{output_video_filepath} successfully"
            )
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)


def is_available_language(language: str) -> bool:
    language = str(language)
    if not language:
        return True
    else:
        return is_iso_language(language)


def config_pre_check(one_mission_config: dict, all_output_filepath_set: set):
    config: dict = one_mission_config
    if config["type"] == "single":
        if not os.path.isfile(config["input_video_filepath"]) and all(
            os.path.abspath(config["input_video_filepath"])
            != os.path.abspath(filepath)
            for filepath in all_output_filepath_set
        ):
            raise ValueError(
                f"input video filepath: "
                f"{config['input_video_filepath']} "
                f"is not a file."
            )
        for external_subtitle_info in config["external_subtitle_info_list"]:
            if not os.path.isfile(external_subtitle_info["filepath"]):
                raise ValueError(
                    f"filepath of external subtitle: "
                    f"{external_subtitle_info['filepath']} "
                    f"is not a file."
                )
            if isinstance(external_subtitle_info["language"], str):
                if not is_available_language(
                    external_subtitle_info["language"]
                ):
                    raise ValueError(
                        f"language of external subtitle: "
                        f"{external_subtitle_info['language']} "
                        f"is not available."
                    )
            elif isinstance(external_subtitle_info["language"], list):
                for language in external_subtitle_info["language"]:
                    if not is_available_language(language):
                        raise ValueError(
                            f"language of external subtitle: "
                            f"{language} "
                            f"is not available."
                        )
            else:
                raise TypeError(
                    f"type of external_subtitle_info['language'] "
                    f"must be str or list, instead of "
                    f"{type(external_subtitle_info['language'])}"
                )
        for external_audio_info in config["external_audio_info_list"]:
            if not os.path.isfile(external_audio_info["filepath"]):
                raise ValueError(
                    f"filepath of external audio: "
                    f"{external_audio_info['filepath']} "
                    f"is not a file."
                )
            if isinstance(external_audio_info["language"], str):
                if not is_available_language(external_audio_info["language"]):
                    raise ValueError(
                        f"language of external audio: "
                        f"{external_audio_info['language']} "
                        f"is not available."
                    )
            elif isinstance(external_audio_info["language"], list):
                for language in external_audio_info["language"]:
                    if not is_available_language(language):
                        raise ValueError(
                            f"language of external audio: "
                            f"{language} "
                            f"is not available."
                        )
            else:
                raise TypeError(
                    f"type of external_audio_info['language'] "
                    f"must be str or list, instead of "
                    f"{type(external_audio_info['language'])}"
                )

        if config["external_chapter_info"]["filepath"]:
            if not os.path.isfile(config["external_chapter_info"]["filepath"]):
                raise ValueError(
                    f"filepath of external chapter: "
                    f"{config['external_chapter_info']['filepath']} "
                    f"is not a file."
                )

    elif config["type"] == "series":
        if not os.path.isdir(config["input_video_dir"]):
            raise ValueError(
                f"input video dir: "
                f"{config['input_video_dir']} "
                f"is not a dir."
            )

        if not any(
            re.search(config["input_video_filename_reexp"], filename)
            for filename in os.listdir(config["input_video_dir"])
        ):
            raise ValueError(
                f"input_video_filename_reexp: "
                f"{config['input_video_filename_reexp']} "
                f"can not match filename in "
                f"{config['input_video_dir']}"
            )
        for external_subtitle_info in config["external_subtitle_info_list"]:
            if not os.path.isdir(external_subtitle_info["subtitle_dir"]):
                raise ValueError(
                    f"subtitle dir of external subtitle: "
                    f"{external_subtitle_info['subtitle_dir']} "
                    f"is not a dir."
                )
            if not any(
                re.search(
                    external_subtitle_info["subtitle_filename_reexp"], filename
                )
                for filename in os.listdir(
                    external_subtitle_info["subtitle_dir"]
                )
            ):
                raise ValueError(
                    f"subtitle filename reexp of external subtitle: "
                    f"{external_subtitle_info['subtitle_filename_reexp']} "
                    f"can not match filename in "
                    f"{external_subtitle_info['subtitle_dir']}"
                )

            if isinstance(external_subtitle_info["language"], str):
                if not is_available_language(
                    external_subtitle_info["language"]
                ):
                    raise ValueError(
                        f"language of external subtitle: "
                        f"{external_subtitle_info['language']} "
                        f"is not available."
                    )
            elif isinstance(external_subtitle_info["language"], list):
                for language in external_subtitle_info["language"]:
                    if not is_available_language(language):
                        raise ValueError(
                            f"language of external subtitle: "
                            f"{language} "
                            f"is not available."
                        )
            else:
                raise TypeError(
                    f"type of external_subtitle_info['language'] "
                    f"must be str or list, instead of "
                    f"{type(external_subtitle_info['language'])}"
                )
        for external_audio_info in config["external_audio_info_list"]:
            if not os.path.isdir(external_audio_info["audio_dir"]):
                raise ValueError(
                    f"audio dir of external audio: "
                    f"{external_audio_info['audio_dir']} "
                    f"is not a dir."
                )
            if not any(
                re.search(
                    external_audio_info["audio_filename_reexp"], filename
                )
                for filename in os.listdir(external_audio_info["audio_dir"])
            ):
                raise ValueError(
                    f"audio filename reexp of external audio: "
                    f"{external_audio_info['audio_filename_reexp']} "
                    f"can not match filename in "
                    f"{external_audio_info['audio_dir']}"
                )

            if isinstance(external_audio_info["language"], str):
                if not is_available_language(external_audio_info["language"]):
                    raise ValueError(
                        f"language of external audio: "
                        f"{external_audio_info['language']} "
                        f"is not available."
                    )
            elif isinstance(external_audio_info["language"], list):
                for language in external_audio_info["language"]:
                    if not is_available_language(language):
                        raise ValueError(
                            f"language of external audio: "
                            f"{language} "
                            f"is not available."
                        )
            else:
                raise TypeError(
                    f"type of external_audio_info['language'] "
                    f"must be str or list, instead of "
                    f"{type(external_audio_info['language'])}"
                )

        if config["external_chapter_info"]["chapter_dir"]:
            if not os.path.isdir(
                config["external_chapter_info"]["chapter_dir"]
            ):
                raise ValueError(
                    f"chapter dir: "
                    f"{config['external_chapter_info']['chapter_dir']} "
                    f"is not a dir."
                )

            if not any(
                re.search(
                    config["external_chapter_info"]["chapter_filename_reexp"],
                    filename,
                )
                for filename in os.listdir(
                    config["external_chapter_info"]["chapter_dir"]
                )
            ):
                raise ValueError(
                    f"chapter_filename_reexp: "
                    f"{config['external_chapter_info']['chapter_filename_reexp']} "
                    f"can not match filename in "
                    f"{config['external_chapter_info']['chapter_dir']}"
                )
    else:
        raise ValueError(f"unkonwn type: {config['type']}")

    constant = global_constant()

    available_package_format_set: set = constant.available_package_format_set
    if config["package_format"] not in available_package_format_set:
        raise RangeError(
            message=(
                f"{config['package_format']} is not an available "
                "package_format"
            ),
            valid_range=str(available_package_format_set),
        )

    available_video_process_option_set: set = constant.available_video_process_option_set
    if (
        config["video_process_option"]
        not in available_video_process_option_set
    ):
        raise RangeError(
            message=(
                f"{config['video_process_option']} is not an available "
                "video_process_option"
            ),
            valid_range=str(available_video_process_option_set),
        )

    if not is_available_language(config["video_language"]):
        raise ValueError(
            f"language of video: {config['video_language']} is not available."
        )

    available_frame_server_set: set = constant.available_frame_server_set
    if config["frame_server"] not in available_frame_server_set:
        raise RangeError(
            message=(
                f"{config['frame_server']} is not an available " "frame_server"
            ),
            valid_range=str(available_frame_server_set),
        )

    if config["frame_server_template_filepath"]:
        if not os.path.isfile(config["frame_server_template_filepath"]):
            raise ValueError(
                f"frame_server_template_filepath: "
                f"{config['frame_server_template_filepath']} "
                f"is not a file."
            )

    if "subtitle_filepath" in config["frame_server_template_config"].keys():
        if config["frame_server_template_config"]["subtitle_filepath"]:
            if not os.path.isfile(
                config["frame_server_template_config"]["subtitle_filepath"]
            ):
                raise ValueError(
                    f"subtitle_filepath in frame_server_template_config: "
                    f"{config['frame_server_template_config']['subtitle_filepath']} "
                    f"is not a file."
                )

    available_video_transcoding_method_set: set = constant.available_video_transcoding_method_set
    if (
        config["video_transcoding_method"]
        not in available_video_transcoding_method_set
    ):
        raise RangeError(
            message=(
                f"{config['video_transcoding_method']} is not an available "
                "video_transcoding_method"
            ),
            valid_range=str(available_video_transcoding_method_set),
        )

    available_output_frame_rate_mode_set: set = constant.available_output_frame_rate_mode_set
    if (
        config["output_frame_rate_mode"]
        not in available_output_frame_rate_mode_set
    ):
        raise RangeError(
            message=(
                f"{config['output_frame_rate_mode']} is not an available "
                "output_frame_rate_mode"
            ),
            valid_range=str(available_output_frame_rate_mode_set),
        )

    available_output_dynamic_range_mode_set: set = constant.available_output_dynamic_range_mode_set
    if (
        config["output_dynamic_range_mode"]
        not in available_output_dynamic_range_mode_set
    ):
        raise RangeError(
            message=(
                f"{config['output_dynamic_range_mode']} is not an available "
                "output_dynamic_range_mode"
            ),
            valid_range=str(available_output_dynamic_range_mode_set),
        )

    available_audio_prior_option_set: set = constant.available_audio_prior_option_set
    if config["audio_prior_option"] not in available_audio_prior_option_set:
        raise RangeError(
            message=(
                f"{config['audio_prior_option']} is not an available "
                "audio_prior_option"
            ),
            valid_range=str(available_audio_prior_option_set),
        )

    available_external_audio_process_option_set: set = constant.available_external_audio_process_option_set
    if (
        config["external_audio_process_option"]
        not in available_external_audio_process_option_set
    ):
        raise RangeError(
            message=(
                f"{config['external_audio_process_option']} is not an available "
                "external_audio_process_option"
            ),
            valid_range=str(available_external_audio_process_option_set),
        )

    available_internal_audio_track_to_process_set: set = constant.available_internal_audio_track_to_process_set
    if (
        config["internal_audio_track_to_process"]
        not in available_internal_audio_track_to_process_set
    ):
        raise RangeError(
            message=(
                f"{config['internal_audio_track_to_process']} is not an available "
                "internal_audio_track_to_process"
            ),
            valid_range=str(available_internal_audio_track_to_process_set),
        )

    available_internal_audio_process_option_set: set = constant.available_internal_audio_process_option_set
    if (
        config["internal_audio_process_option"]
        not in available_internal_audio_process_option_set
    ):
        raise RangeError(
            message=(
                f"{config['internal_audio_process_option']} is not an available "
                "internal_audio_process_option"
            ),
            valid_range=str(available_internal_audio_process_option_set),
        )
    for internal_audio_info in config["internal_audio_info_list"]:
        if not is_available_language(internal_audio_info["language"]):
            raise ValueError(
                f"language of internal audio: "
                f"{internal_audio_info['language']} "
                f"is not available."
            )

    available_subtitle_prior_option_set: set = constant.available_subtitle_prior_option_set
    if (
        config["subtitle_prior_option"]
        not in available_subtitle_prior_option_set
    ):
        raise RangeError(
            message=(
                f"{config['subtitle_prior_option']} is not an available "
                "subtitle_prior_option"
            ),
            valid_range=str(available_subtitle_prior_option_set),
        )
    for internal_subtitle_info in config["internal_subtitle_info_list"]:
        if not is_available_language(internal_subtitle_info["language"]):
            raise ValueError(
                f"language of internal subtitle: "
                f"{internal_subtitle_info['language']} "
                f"is not available."
            )

    for filepath in config["external_attachment_filepath_list"]:
        if not os.path.isfile(filepath):
            raise ValueError(
                f"external_attachment_filepath: {filepath} is not a file."
            )


def get_output_filepath_set(one_mission_config: dict):
    config = one_mission_config
    output_filepath_set: set = set()
    if config["type"] == "single":
        output_filepath_set.add(
            os.path.join(
                config["output_video_dir"],
                config["output_video_name"] + "." + config["package_format"],
            )
        )
    elif config["type"] == "series":
        for episode in config["episode_list"]:
            output_video_name: str = config[
                "output_video_name_template_str"
            ].format(episode=episode) + "." + config["package_format"]

            output_filepath_set.add(
                os.path.join(config["output_video_dir"], output_video_name)
            )
    return output_filepath_set


def transcode_all_missions(
    config_json_filepath: str, param_template_json_filepath: str
):
    if not isinstance(config_json_filepath, str):
        raise TypeError(
            f"type of config_json_filepath must be str "
            f"instead of {type(config_json_filepath)}"
        )

    if not isinstance(param_template_json_filepath, str):
        raise TypeError(
            f"type of param_template_json_filepath must be str "
            f"instead of {type(param_template_json_filepath)}"
        )

    if not os.path.isfile(config_json_filepath):
        raise FileNotFoundError(
            f"input json file cannot be found with {config_json_filepath}"
        )

    if not os.path.isfile(param_template_json_filepath):
        raise FileNotFoundError(
            f"input json file cannot be found with "
            f"{param_template_json_filepath}"
        )

    config_dict: dict = load_config(config_json_filepath)
    param_template_dict: dict = load_config(param_template_json_filepath)
    param_template_key_set: set = set(param_template_dict.keys())
    basic_config_dict: dict = config_dict["basic_config"]

    main_logger = get_logger(basic_config_dict["log_config_filepath"])

    main_logger_init_info_str: str = (
        f"transcode all missions: initialize "
        f"main logger {main_logger} successfully."
    )
    g_logger.log(logging.INFO, main_logger_init_info_str)
    
    

    time.sleep(basic_config_dict["delay_start_sec"])

    all_mission_config_list: list = config_dict["all_mission_config"]
    all_output_filepath_set: set = set()
    new_all_mission_config_list: list = []
    for mission_config in all_mission_config_list:
        mission_config["universal_config"] = dict(
            dict(
                cache_dir=mission_config["universal_config"]["cache_dir"],
                package_format=mission_config["universal_config"][
                    "package_format"
                ],
                thread_bool=mission_config["universal_config"]["thread_bool"],
            ),
            **mission_config["universal_config"]["video_related_config"],
            **mission_config["universal_config"]["audio_related_config"],
            **mission_config["universal_config"]["subtitle_related_config"],
            **mission_config["universal_config"]["chapter_related_config"],
            **mission_config["universal_config"]["attachment_related_config"],
        )
        mission_config = dict(
            dict(type=mission_config["type"]),
            **mission_config["type_related_config"],
            **mission_config["universal_config"],
        )

        config_pre_check(
            mission_config, all_output_filepath_set=all_output_filepath_set
        )

        episode_list_re_exp: str = "(\\d+)~(\\d+)"
        for key in mission_config.keys():
            if key == "episode_list" and isinstance(mission_config[key], str):
                re_result = re.search(episode_list_re_exp, mission_config[key])
                if not re_result:
                    raise ValueError(
                        "format of episode_list str is inaccurate."
                    )
                first_episode: int = int(re_result.group(1))
                last_episode: int = int(re_result.group(2))
                step: int = 1
                if first_episode > last_episode:
                    step = -1
                mission_config[key] = [
                    episode
                    for episode in range(
                        first_episode, last_episode + step, step
                    )
                ]
                continue
            if (
                key in param_template_key_set
                and mission_config[key]
                and isinstance(mission_config[key], str)
            ):
                mission_config[key] = param_template_dict[key][
                    mission_config[key]
                ]

        all_output_filepath_set |= get_output_filepath_set(mission_config)

        if mission_config["type"] == "series":
            for episode in mission_config["segmented_transcode_config"].keys():
                for index in range(
                    len(mission_config["segmented_transcode_config"][episode])
                ):
                    for key in mission_config["segmented_transcode_config"][
                        episode
                    ][index].keys():
                        if key in param_template_key_set and isinstance(
                            mission_config["segmented_transcode_config"][
                                episode
                            ][index][key],
                            str,
                        ):
                            mission_config["segmented_transcode_config"][
                                episode
                            ][index][key] = param_template_dict[key][
                                mission_config["segmented_transcode_config"][
                                    episode
                                ][index][key]
                            ]
        elif mission_config["type"] == "single":
            for index in range(
                len(mission_config["segmented_transcode_config_list"])
            ):
                for key in mission_config["segmented_transcode_config_list"][
                    index
                ]:
                    if key in param_template_key_set and isinstance(
                        mission_config["segmented_transcode_config_list"][
                            index
                        ][key],
                        str,
                    ):
                        mission_config["segmented_transcode_config_list"][
                            index
                        ][key] = param_template_dict[key][
                            mission_config["segmented_transcode_config_list"][
                                index
                            ][key]
                        ]

        if not is_printable(mission_config["cache_dir"]):
            old_cache_dir = mission_config["cache_dir"]
            mission_config["cache_dir"] = get_printable(
                mission_config["cache_dir"]
            )
            warning_str: str = (
                f"pre-check: there is unprintable char in "
                f"cache_dir: {old_cache_dir} ,"
                f"replace to {mission_config['cache_dir']}"
            )
            g_logger.log(logging.WARNING, warning_str)
            warnings.warn(warning_str, RuntimeWarning)
        
        
        
        
        
        
        
        
        
        

        
        
        
        
        
        
        

        Config: namedtuple = namedtuple("Config", sorted(mission_config))
        mission_config: namedtuple = Config(**mission_config)

        new_all_mission_config_list.append(mission_config)

    for mission_config in new_all_mission_config_list:
        if mission_config.type == "series":
            series_transcoding_mission = SeriesVideoTranscoding(
                input_video_dir=mission_config.input_video_dir,
                input_video_filename_reexp=mission_config.input_video_filename_reexp,
                external_subtitle_info_list=mission_config.external_subtitle_info_list,
                output_video_dir=mission_config.output_video_dir,
                output_video_name_template_str=mission_config.output_video_name_template_str,
                cache_dir=mission_config.cache_dir,
                episode_list=mission_config.episode_list,
                config=mission_config,
            )
            series_transcoding_mission.transcode()

        elif mission_config.type == "single":
            single_transcoding_mission = CompleteVideoTranscoding(
                input_video_filepath=mission_config.input_video_filepath,
                output_video_dir=mission_config.output_video_dir,
                output_video_name=mission_config.output_video_name,
                cache_dir=mission_config.cache_dir,
                config=mission_config,
            )
            output_video_filepath: str = single_transcoding_mission.transcode()

            end_info_str: str = (
                f"transcode single: transcoding "
                f"{mission_config.input_video_filepath} to "
                f"{output_video_filepath} successfully"
            )
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)

        else:
            raise ValueError("type must be series or single")


