"""
    track.py media track module of media_master
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
import os


class Track(object):

    video_track_type: str = "video"
    audio_track_type: str = "audio"
    text_track_type: str = "text"
    menu_track_type: str = "menu"

    def __init__(self, track_type: str):
        if not isinstance(track_type, str):
            raise TypeError(
                f"type of track_type must be str instead of \
{type(track_type)}"
            )

        self.track_type = track_type


class RepeatableTrack(Track):

    def __init__(
        self,
        track_index: int,
        track_type: str,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):
        if not isinstance(track_index, int):
            raise TypeError(
                f"type of track_index must be int instead of \
{type(track_index)}"
            )

        if track_index < 0:
            raise RangeError(
                message=f"value of track_index must in [0,inf)",
                valid_range=f"[0,inf)",
            )
        self.track_index = track_index

        if not isinstance(track_format, str):
            raise TypeError(
                f"type of track_format must be str instead of \
{type(track_format)}"
            )
        self.track_format = track_format

        super(RepeatableTrack, self).__init__(track_type)

        if not isinstance(duration_ms, int):
            raise TypeError(
                f"type of duration_ms must be int instead of \
{type(duration_ms)}"
            )
        if duration_ms <= 0 and duration_ms != -1:
            raise RangeError(
                message=f"value of duration_ms must in (0,inf) and -1",
                valid_range=f"(0,inf) and -1",
            )
        self.duration_ms = duration_ms

        if not isinstance(bit_rate_bps, int):
            raise TypeError(
                f"type of bit_rate_bps must be int instead of \
{type(bit_rate_bps)}"
            )
        if bit_rate_bps <= 0 and bit_rate_bps != -1:
            raise RangeError(
                message=f"value of bit_rate_bps must in (0,inf) and -1",
                valid_range=f"(0,inf) and -1",
            )
        self.bit_rate_bps = bit_rate_bps

        if not isinstance(delay_ms, int):
            raise TypeError(
                f"type of delay_ms must be int instead of \
{type(delay_ms)}"
            )
        if delay_ms < 0:
            raise RangeError(
                message=f"value of delay_ms must in (0,inf)",
                valid_range=f"(0,inf)",
            )
        self.delay_ms = delay_ms

        if not isinstance(stream_size_byte, int):
            raise TypeError(
                f"type of stream_size_byte must be int instead of \
{type(stream_size_byte)}"
            )
        if stream_size_byte <= 0 and stream_size_byte != -1:
            raise RangeError(
                message=f"value of stream_size_byte must in (0,inf) and -1",
                valid_range=f"(0,inf) and -1",
            )
        self.stream_size_byte = stream_size_byte

        if not isinstance(title, str):
            raise TypeError(
                f"type of title must be str instead of \
{type(title)}"
            )
        self.title = title

        if not isinstance(language, str):
            raise TypeError(
                f"type of language must be str instead of \
{type(language)}"
            )
        self.language = language

        if not isinstance(default_bool, bool):
            raise TypeError(
                f"type of default_bool must be bool instead of \
{type(default_bool)}"
            )
        self.default_bool = default_bool

        if not isinstance(forced_bool, bool):
            raise TypeError(
                f"type of forced_bool must be bool instead of \
{type(forced_bool)}"
            )
        self.forced_bool = forced_bool


class MenuTrack(Track):

    needed_menu_info_key_set: set = {
        "title",
        "start_time",
        "end_time",
        "language",
    }

    non_empty_menu_info_key_set: set = {"title", "start_time"}

    def __init__(self, menu_info_list: list):
        if not isinstance(menu_info_list, list):
            raise TypeError(
                f"type of menu_info_list must be list instead of \
{type(menu_info_list)}"
            )

        for menu_info in menu_info_list:
            if not isinstance(menu_info, dict):
                raise TypeError(
                    f"type of menu_info must be dict instead of \
{type(menu_info)}"
                )
            for field in menu_info.keys():
                if field not in self.needed_menu_info_key_set:
                    raise RangeError(
                        message=f"value of field of menu_info must in \
{self.needed_menu_info_key_set} instead of {field}",
                        valid_range=f"{self.needed_menu_info_key_set}",
                    )
                if (
                    not menu_info[field]
                    and field in self.non_empty_menu_info_key_set
                ):
                    raise ValueError(f"value of {field} can't be empty")

        self.menu_info_list = menu_info_list

        super(MenuTrack, self).__init__(track_type=self.menu_track_type)


class VideoTrack(RepeatableTrack):

    def __init__(
        self,
        track_index: int,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        width: int,
        height: int,
        frame_rate: str,
        frame_count: int,
        color_range: str,
        color_space: str,
        chroma_subsampling: str,
        bit_depth: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):

        if not isinstance(width, int):
            raise TypeError(
                f"type of width must be int instead of \
{type(width)}"
            )
        if width <= 0:
            raise RangeError(
                message=f"value of width must in (0,inf)",
                valid_range=f"(0,inf)",
            )
        self.width = width

        if not isinstance(height, int):
            raise TypeError(
                f"type of height must be int instead of \
{type(height)}"
            )
        if height <= 0:
            raise RangeError(
                message=f"value of height must in (0,inf)",
                valid_range=f"(0,inf)",
            )
        self.height = height

        if not isinstance(frame_rate, str):
            raise TypeError(
                f"type of frame_rate must be str instead of \
{type(frame_rate)}"
            )
        self.frame_rate = frame_rate

        if not isinstance(frame_count, int):
            raise TypeError(
                f"type of frame_count must be int instead of \
{type(frame_count)}"
            )
        if frame_count <= 0 and frame_count != -1:
            raise RangeError(
                message=f"value of frame_count must in (0,inf) and -1",
                valid_range=f"(0,inf) and -1",
            )
        self.frame_count = frame_count

        if not isinstance(color_range, str):
            raise TypeError(
                f"type of color_range must be str instead of \
{type(color_range)}"
            )
        self.color_range = color_range

        if not isinstance(color_space, str):
            raise TypeError(
                f"type of color_space must be str instead of \
{type(color_space)}"
            )
        self.color_space = color_space

        if not isinstance(chroma_subsampling, str):
            raise TypeError(
                f"type of chroma_subsampling must be str instead of \
{type(chroma_subsampling)}"
            )
        self.chroma_subsampling = chroma_subsampling

        if not isinstance(bit_depth, int):
            raise TypeError(
                f"type of bit_depth must be int instead of \
{type(bit_depth)}"
            )
        if bit_depth <= 0 and bit_depth != -1:
            raise RangeError(
                message=f"value of bit_depth must in (0,inf) or -1",
                valid_range=f"(0,inf) or -1",
            )
        self.bit_depth = bit_depth

        super(VideoTrack, self).__init__(
            track_index=track_index,
            track_type=self.video_track_type,
            track_format=track_format,
            duration_ms=duration_ms,
            bit_rate_bps=bit_rate_bps,
            delay_ms=delay_ms,
            stream_size_byte=stream_size_byte,
            title=title,
            language=language,
            default_bool=default_bool,
            forced_bool=forced_bool,
        )


class AudioTrack(RepeatableTrack):

    def __init__(
        self,
        track_index: int,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        bit_depth: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):
        if not isinstance(bit_depth, int):
            raise TypeError(
                f"type of bit_depth must be int instead of \
{type(bit_depth)}"
            )
        if bit_depth <= 0 and bit_depth != -1:
            raise RangeError(
                message=f"value of bit_depth must in (0,inf) or -1",
                valid_range=f"(0,inf) or -1",
            )
        self.bit_depth = bit_depth

        super(AudioTrack, self).__init__(
            track_index=track_index,
            track_type=self.audio_track_type,
            track_format=track_format,
            duration_ms=duration_ms,
            bit_rate_bps=bit_rate_bps,
            delay_ms=delay_ms,
            stream_size_byte=stream_size_byte,
            title=title,
            language=language,
            default_bool=default_bool,
            forced_bool=forced_bool,
        )


class TextTrack(RepeatableTrack):

    def __init__(
        self,
        track_index: int,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):
        super(TextTrack, self).__init__(
            track_index=track_index,
            track_type=self.text_track_type,
            track_format=track_format,
            duration_ms=duration_ms,
            bit_rate_bps=bit_rate_bps,
            delay_ms=delay_ms,
            stream_size_byte=stream_size_byte,
            title=title,
            language=language,
            default_bool=default_bool,
            forced_bool=forced_bool,
        )


class IntermediateFile(object):

    def __init__(self, filepath: str):
        if not isinstance(filepath, str):
            raise TypeError(
                f"type of filepath must be str \
instead of {type(filepath)}"
            )
        if filepath and not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"input file cannot be found with {filepath}"
            )
        self.filepath: str = filepath


class VideoTrackFile(VideoTrack, IntermediateFile):
    def __init__(
        self,
        filepath: str,
        track_index: int,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        width: int,
        height: int,
        frame_rate: str,
        frame_count: int,
        color_range: str,
        color_space: str,
        chroma_subsampling: str,
        bit_depth: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):
        VideoTrack.__init__(
            self,
            track_index=track_index,
            track_format=track_format,
            duration_ms=duration_ms,
            bit_rate_bps=bit_rate_bps,
            width=width,
            height=height,
            frame_rate=frame_rate,
            frame_count=frame_count,
            color_range=color_range,
            color_space=color_space,
            chroma_subsampling=chroma_subsampling,
            bit_depth=bit_depth,
            delay_ms=delay_ms,
            stream_size_byte=stream_size_byte,
            title=title,
            language=language,
            default_bool=default_bool,
            forced_bool=forced_bool,
        )
        IntermediateFile.__init__(self, filepath=filepath)


class AudioTrackFile(AudioTrack, IntermediateFile):
    def __init__(
        self,
        filepath: str,
        track_index: int,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        bit_depth: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):
        AudioTrack.__init__(
            self,
            track_index=track_index,
            track_format=track_format,
            duration_ms=duration_ms,
            bit_rate_bps=bit_rate_bps,
            bit_depth=bit_depth,
            delay_ms=delay_ms,
            stream_size_byte=stream_size_byte,
            title=title,
            language=language,
            default_bool=default_bool,
            forced_bool=forced_bool,
        )
        IntermediateFile.__init__(self, filepath=filepath)


class TextTrackFile(TextTrack, IntermediateFile):
    def __init__(
        self,
        filepath: str,
        track_index: int,
        track_format: str,
        duration_ms: int,
        bit_rate_bps: int,
        delay_ms: int,
        stream_size_byte: int,
        title: str,
        language: str,
        default_bool: bool,
        forced_bool: bool,
    ):
        TextTrack.__init__(
            self,
            track_index=track_index,
            track_format=track_format,
            duration_ms=duration_ms,
            bit_rate_bps=bit_rate_bps,
            delay_ms=delay_ms,
            stream_size_byte=stream_size_byte,
            title=title,
            language=language,
            default_bool=default_bool,
            forced_bool=forced_bool,
        )
        IntermediateFile.__init__(self, filepath=filepath)


class MenuTrackFile(IntermediateFile):
    def __init__(self, filepath: str):
        super(MenuTrackFile, self).__init__(filepath=filepath)
