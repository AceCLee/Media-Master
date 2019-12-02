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
import sys
import time
import warnings
from collections import namedtuple

from pymediainfo import MediaInfo


from .audio import (
    transcode_audio_opus,
    transcode_audio_qaac,
    transcode_audio_wav_2_flac,
)
from .log import get_logger
from .util import (
    multiplex,
    remultiplex_one_file,
    extract_all_attachments,
    extract_all_subtitles,
    extract_audio_track,
    extract_chapter,
    load_config,
    copy_video,
    get_proper_frame_rate,
    resort,
)
from .video import (
    SegmentedConfigX265VspipeTranscoding,
    GopX265VspipeVideoTranscoding,
    NvencVideoTranscoding,
    X264VspipeVideoTranscoding,
)
from .error import RangeError
from .track import VideoTrackFile, AudioTrackFile, TextTrackFile, MenuTrackFile

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

    def __init__(
        self,
        input_video_filepath: str,
        output_video_dir: str,
        output_video_filename: str,
        cache_dir: str,
        config: namedtuple,
    ):
        self._input_video_filepath: str = input_video_filepath
        self._output_video_dir: str = output_video_dir
        self._output_video_filename: str = output_video_filename
        self._cache_dir: str = cache_dir
        self._config: namedtuple = config
        if not os.path.isdir(self._cache_dir):
            os.makedirs(self._cache_dir)
        if not os.path.isdir(self._output_video_dir):
            os.makedirs(self._output_video_dir)
        self._remove_filepath_set: set = set()

    def transcode(self) -> str:
        self._pre_multiplex()
        self._subtitle_process()
        self._chapter_process()
        self._attachment_process()
        self._audio_process()
        self._video_stream_process()
        self._multiplex_all()
        self._delete_cache_file()

        return self._output_video_filepath

    def _pre_multiplex(self):
        unreliable_filename_extension_set: set = {".m2ts"}
        input_full_filename: str = os.path.basename(self._input_video_filepath)
        filename, extension = os.path.splitext(input_full_filename)
        if extension in unreliable_filename_extension_set:
            new_filename: str = f"{filename}_pre_multiplex"
            new_input_filepath: str = remultiplex_one_file(
                input_filepath=self._input_video_filepath,
                output_file_dir=self._cache_dir,
                output_file_name=new_filename,
            )
            self._input_video_filepath = new_input_filepath

    def _audio_transcode(self, audio_track_file_list: list) -> list:
        transcoded_audio_track_file_list: list = []
        for index, audio_track_file in enumerate(audio_track_file_list):
            transcoded_audio_filename: str = (
                self._output_video_filename + f"_audio_index_{index}"
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
                    transcode_audio_wav_2_flac(
                        audio_track_file.filepath,
                        self._cache_dir,
                        transcoded_audio_filename,
                        self._config.audio_transcoding_cmd_param_template,
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

            return transcoded_audio_track_file_list

    def _audio_process(self):
        internal_audio_process_available_option_set: set = {
            "copy",
            "transcode",
            "skip",
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
                self._output_video_filename,
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
                else:
                    break

            if self._config.internal_audio_track_order_list:
                internal_audio_track_file_list = resort(
                    src=internal_audio_track_file_list,
                    order_list=self._config.internal_audio_track_order_list,
                )

        external_audio_track_file_list: list = []
        if self._config.external_audio_info_list:
            for index, external_audio_info in enumerate(
                self._config.external_audio_info_list
            ):
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
                    stream_size_byte=int(audio_info["stream_size"]),
                    title=external_audio_info["title"],
                    language=external_audio_info["language"],
                    default_bool=True if index == 0 else False,
                    forced_bool=False,
                )
                external_audio_track_file_list.append(audio_track_file)

        output_internal_audio_track_file_list: list = []
        if self._config.internal_audio_process_option == "transcode":
            output_internal_audio_track_file_list += self._audio_transcode(
                internal_audio_track_file_list
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
                    external_audio_track_file_list
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
        for index, subtitle_info in enumerate(external_subtitle_info_list):
            text_track_file = TextTrackFile(
                filepath=subtitle_info["filepath"],
                track_index=0,
                track_format=subtitle_info["filepath"].split(".")[-1],
                duration_ms=-1,
                bit_rate_bps=-1,
                delay_ms=subtitle_info["delay_ms"],
                stream_size_byte=-1,
                title=subtitle_info["title"],
                language=subtitle_info["language"],
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
                    self._output_video_filename,
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
                    order_list=self._config.internal_subtitle_track_order_list,
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
        chapter_filename_extension: str = ".xml"
        if self._config.external_chapter_info["filepath"]:
            if self._config.external_chapter_info["filepath"].endswith(
                chapter_filename_extension
            ):
                self._menu_track_file = MenuTrackFile(
                    filepath=self._config.external_chapter_info["filepath"]
                )
            else:
                self._menu_track_file = extract_chapter(
                    self._config.external_chapter_info["filepath"],
                    self._cache_dir,
                    self._output_video_filename,
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
                self._output_video_filename,
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
        if self._config.video_process_option == "copy":
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

            video_info_key_set: set = set(video_info_dict.keys())

            play_frame_rate: str = get_proper_frame_rate(
                video_info_dict=video_info_dict,
                video_info_key_set=video_info_key_set,
                original_fps=True,
            )
            if not play_frame_rate:
                raise KeyError(
                    f"video track of {self._input_video_filepath} "
                    f"does not have frame_rate info."
                )

            color_range_key: str = "color_range"
            if color_range_key in video_info_key_set:
                color_range: str = video_info_dict[color_range_key].lower()
            else:
                color_range: str = "limited"

            video_track_file: VideoTrackFile = VideoTrackFile(
                filepath=self._input_video_filepath,
                track_index=int(video_info_dict["streamorder"]),
                track_format=video_info_dict["format"].lower(),
                duration_ms=int(float(video_info_dict["duration"])),
                bit_rate_bps=int(video_info_dict["bit_rate"])
                if "bit_rate" in video_info_dict.keys()
                else -1,
                width=video_info_dict["width"],
                height=video_info_dict["height"],
                frame_rate=play_frame_rate,
                frame_count=int(video_info_dict["frame_count"]),
                color_range=color_range,
                color_space=video_info_dict["color_space"],
                chroma_subsampling=video_info_dict["chroma_subsampling"],
                bit_depth=int(video_info_dict["bit_depth"]),
                delay_ms=int(video_info_dict["delay"])
                if "delay" in video_info_dict.keys()
                else 0,
                stream_size_byte=int(video_info_dict["stream_size"])
                if "stream_size" in video_info_dict.keys()
                else -1,
                title=self._config.video_title,
                language=self._config.video_language,
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

            self._output_video_track_file = (
                self._video_track_file
            ) = video_track_file

        elif self._config.video_process_option == "transcode":
            self._video_track_file = copy_video(
                self._input_video_filepath, self._cache_dir
            )

            self._remove_filepath_set.add(self._video_track_file.filepath)

            other_config: dict = dict(
                video_play_fps=self._video_track_file.frame_rate,
                input_full_range_bool=True
                if self._video_track_file.color_range == "full"
                else False,
                output_full_range_bool=self._config.output_full_range_bool,
                input_video_width=self._video_track_file.width,
                input_video_height=self._video_track_file.height,
            )

            if self._config.frame_server == "vspipe":
                if self._config.video_transcoding_method == "x265":
                    if self._config.segmented_transcode_config_list:
                        x265_transcoding_mission = SegmentedConfigX265VspipeTranscoding(
                            self._video_track_file.filepath,
                            self._config.frame_server_template_filepath,
                            self._cache_dir,
                            self._output_video_filename,
                            copy.deepcopy(
                                self._config.frame_server_template_config
                            ),
                            self._cache_dir,
                            self._output_video_filename,
                            copy.deepcopy(
                                self._config.video_transcoding_cmd_param_template
                            ),
                            copy.deepcopy(other_config),
                            self._config.gop_segmented_transcode_config[
                                "gop_frame_cnt"
                            ],
                            0,
                            self._video_track_file.frame_count - 1,
                            self._config.segmented_transcode_config_list,
                        )
                    else:
                        x265_transcoding_mission = GopX265VspipeVideoTranscoding(
                            self._video_track_file.filepath,
                            self._config.frame_server_template_filepath,
                            self._cache_dir,
                            self._output_video_filename,
                            copy.deepcopy(
                                self._config.frame_server_template_config
                            ),
                            self._cache_dir,
                            self._output_video_filename,
                            copy.deepcopy(
                                self._config.video_transcoding_cmd_param_template
                            ),
                            copy.deepcopy(other_config),
                            self._config.gop_segmented_transcode_config[
                                "gop_frame_cnt"
                            ],
                            0,
                            self._video_track_file.frame_count - 1,
                        )
                    result = x265_transcoding_mission.transcode()
                    compressed_video_cache_filepath: str = result
                elif self._config.video_transcoding_method == "x264":
                    x264_transcoding_mission = X264VspipeVideoTranscoding(
                        self._video_track_file.filepath,
                        self._config.frame_server_template_filepath,
                        self._cache_dir,
                        self._output_video_filename,
                        copy.deepcopy(
                            self._config.frame_server_template_config
                        ),
                        self._cache_dir,
                        self._output_video_filename,
                        copy.deepcopy(
                            self._config.video_transcoding_cmd_param_template
                        ),
                        copy.deepcopy(other_config),
                    )
                    result_tuple: tuple = x264_transcoding_mission.transcode()
                    compressed_video_cache_filepath: str = result_tuple[0]
                    self._encode_fps = result_tuple[1]
                    self._encode_bitrate = result_tuple[2]
                else:
                    raise RangeError(
                        message=(
                            f"Unknown video_transcoding_method with vspipe: "
                            f"{self._config.video_transcoding_method}"
                        ),
                        valid_range=str({"x265", "x264"}),
                    )
            elif self._config.frame_server == "":
                if self._config.video_transcoding_method == "nvenc":
                    nvenc_transcoding_mission = NvencVideoTranscoding(
                        self._input_video_filepath,
                        self._cache_dir,
                        self._output_video_filename,
                        copy.deepcopy(
                            self._config.video_transcoding_cmd_param_template
                        ),
                        copy.deepcopy(other_config),
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
            frame_count: int = int(video_info_dict["frame_count"])
            if 0 < abs(frame_count - self._video_track_file.frame_count) < 3:
                cnt_ne_str: str = (
                    f"transcode warning: "
                    f"source frame count:{self._video_track_file.frame_count}"
                    f" != output frame count:{frame_count}"
                )
                g_logger.log(logging.WARNING, cnt_ne_str)
                warnings.warn(cnt_ne_str, RuntimeWarning)
            elif frame_count != self._video_track_file.frame_count:
                raise ValueError(
                    f"transcode error: "
                    f"source frame count:{self._video_track_file.frame_count} "
                    f"!= output frame count:{frame_count}"
                )

            self._output_video_track_file = copy.deepcopy(
                self._video_track_file
            )
            self._output_video_track_file.filepath = (
                compressed_video_cache_filepath
            )
            self._output_video_track_file.color_range = (
                "full" if self._config.output_full_range_bool else "limited"
            )
            self._output_video_track_file.title = self._config.video_title
            self._output_video_track_file.language = (
                self._config.video_language
            )
            self._remove_filepath_set.add(compressed_video_cache_filepath)

    def _multiplex_all(self):
        track_info_list: list = [
            {
                "filepath": self._output_video_track_file.filepath,
                "sync_delay": self._output_video_track_file.delay_ms,
                "track_type": self._output_video_track_file.track_type,
                "track_name": self._output_video_track_file.title,
                "language": self._output_video_track_file.language,
                "original_index": self._output_video_track_file.track_index
                if self._config.video_process_option == "copy"
                else 0,
            }
        ]
        track_info_list += [
            dict(
                filepath=audio_track_file.filepath,
                sync_delay=audio_track_file.delay_ms,
                track_type=audio_track_file.track_type,
                track_name=audio_track_file.title,
                language=audio_track_file.language,
                original_index=0,
            )
            for audio_track_file in self._output_audio_track_file_list
        ]

        track_info_list += [
            dict(
                filepath=text_track_file.filepath,
                sync_delay=text_track_file.delay_ms,
                track_type="subtitle",
                track_name=text_track_file.title,
                language=text_track_file.language,
                original_index=0,
            )
            for text_track_file in self._output_text_track_file_list
        ]

        self._output_video_filepath: str = multiplex(
            copy.deepcopy(track_info_list),
            self._output_video_dir,
            self._output_video_filename,
            chapters_filepath=self._menu_track_file.filepath,
            attachments_filepath_set=self._attachments_filepath_set,
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
                episode: str = re_result.group(1)
                if episode in video_info.keys():
                    raise RuntimeError(
                        f"repetitive episode in {self._input_video_dir}"
                    )
                video_info[str(int(episode))] = dict(
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
                        else 0,
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
                        else 0,
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
        if self._config.external_subtitle_info_list:
            length_list: list = []
            length_list.append(len(video_info))
            length_list += [
                len(subtitle_info) for subtitle_info in subtitle_info_list
            ]
            if max(length_list) != min(length_list):
                video_filename_list: list = [
                    os.path.basename(one_video_info["filepath"])
                    for one_video_info in video_info.values()
                ]
                print(video_filename_list, len(video_info), file=sys.stderr)
                for subtitle_info in subtitle_info_list:
                    subtitle_filename_list: list = [
                        os.path.basename(one_subtitle_info["filepath"])
                        for one_subtitle_info in subtitle_info.values()
                    ]
                    print(
                        subtitle_filename_list,
                        len(subtitle_info),
                        file=sys.stderr,
                    )
                raise RuntimeError(
                    f"max episode length is {max(length_list)}, \
min episode length is {min(length_list)}"
                )

        if self._config.external_audio_info_list:
            length_list: list = []
            length_list.append(len(video_info))
            length_list += [len(audio_info) for audio_info in audio_info_list]
            if min(length_list) == 0:
                raise RuntimeError(f"min episode length is 0")
            if max(length_list) != min(length_list):
                video_filename_list: list = [
                    os.path.basename(one_video_info["filepath"])
                    for one_video_info in video_info.values()
                ]
                warning_str: str = f"{video_filename_list} {len(video_info)}"
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)
                for audio_info in audio_info_list:
                    audio_filename_list: list = [
                        os.path.basename(one_audio_info["filepath"])
                        for one_audio_info in audio_info.values()
                    ]
                    warning_str: str = f"{audio_filename_list} {len(audio_info)}"
                    g_logger.log(logging.WARNING, warning_str)
                    warnings.warn(warning_str, RuntimeWarning)
                warning_str: str = f"max episode length is {max(length_list)}, \
min episode length is {min(length_list)}"
                g_logger.log(logging.WARNING, warning_str)
                warnings.warn(warning_str, RuntimeWarning)

        video_filename_list: list = [
            os.path.basename(one_video_info["filepath"])
            for one_video_info in video_info.values()
        ]
        transcode_series_video_debug_str: str = f"transcode series:\
videos:{video_filename_list}"
        g_logger.log(logging.DEBUG, transcode_series_video_debug_str)

        for index, subtitle_info in enumerate(subtitle_info_list):
            subtitle_filename_list: list = [
                os.path.basename(one_subtitle_info["filepath"])
                for one_subtitle_info in subtitle_info.values()
            ]
            transcode_series_subtitle_debug_str: str = f"transcode series:\
subtitles {index}:{subtitle_filename_list}"
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

        start_info_str: str = f"transcode series: starting transcoding \
{self._input_video_dir}"
        print(start_info_str, file=sys.stderr)
        g_logger.log(logging.INFO, start_info_str)
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
                )
                for subtitle_info in subtitle_info_list
            ]
            config["external_audio_info_list"] = [
                dict(
                    filepath=audio_info[str(int(episode_num))]["filepath"],
                    title=audio_info[str(int(episode_num))]["title"],
                    language=audio_info[str(int(episode_num))]["language"],
                    delay_ms=audio_info[str(int(episode_num))]["delay_ms"],
                )
                for audio_info in audio_info_list
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

            start_info_str: str = f"transcode series: starting \
transcoding episode {episode_num}"
            print(start_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, start_info_str)

            current_episode_transcoding = CompleteVideoTranscoding(
                video_filepath,
                self._output_video_dir,
                output_video_filename,
                self._cache_dir,
                config,
            )
            output_video_filepath: str = (
                current_episode_transcoding.transcode()
            )

            end_info_str: str = f"transcode series: \
transcoding episode {episode_num} to \
{output_video_filepath} successfully"
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)


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
            f"input json file cannot be found with \
{config_json_filepath}"
        )

    if not os.path.isfile(param_template_json_filepath):
        raise FileNotFoundError(
            f"input json file cannot be found with \
{param_template_json_filepath}"
        )

    config_dict: dict = load_config(config_json_filepath)
    param_template_dict: dict = load_config(param_template_json_filepath)
    param_template_key_set: set = set(param_template_dict.keys())
    basic_config_dict: dict = config_dict["basic_config"]

    main_logger = get_logger(basic_config_dict["log_config_filepath"])

    main_logger_init_info_str: str = f"transcode all missions: initialize \
main logger {main_logger} successfully."
    g_logger.log(logging.INFO, main_logger_init_info_str)

    time.sleep(basic_config_dict["delay_start_sec"])

    all_mission_config_list: list = config_dict["all_mission_config"]
    for mission_config in all_mission_config_list:
        mission_config["universal_config"] = dict(
            dict(cache_dir=mission_config["universal_config"]["cache_dir"]),
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
            if key in param_template_key_set and isinstance(
                mission_config[key], str
            ):
                mission_config[key] = param_template_dict[key][
                    mission_config[key]
                ]
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

        Config: namedtuple = namedtuple("Config", sorted(mission_config))
        mission_config: namedtuple = Config(**mission_config)

        if mission_config.type == "series":
            series_transcoding_mission = SeriesVideoTranscoding(
                mission_config.input_video_dir,
                mission_config.input_video_filename_reexp,
                mission_config.external_subtitle_info_list,
                mission_config.output_video_dir,
                mission_config.output_video_name_template_str,
                mission_config.cache_dir,
                mission_config.episode_list,
                mission_config,
            )
            series_transcoding_mission.transcode()

        elif mission_config.type == "single":
            single_transcoding_mission = CompleteVideoTranscoding(
                mission_config.input_video_filepath,
                mission_config.output_video_dir,
                mission_config.output_video_name,
                mission_config.cache_dir,
                mission_config,
            )
            output_video_filepath: str = single_transcoding_mission.transcode()

            end_info_str: str = f"transcode single: transcoding \
{mission_config.input_video_filepath} to \
{output_video_filepath} successfully"
            print(end_info_str, file=sys.stderr)
            g_logger.log(logging.INFO, end_info_str)

        else:
            raise ValueError("type must be series or single")


