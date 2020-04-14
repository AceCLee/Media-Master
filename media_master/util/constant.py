"""
    constant.py constant of media info
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

from collections import namedtuple


def global_constant():
    constant_dict: dict = dict(
        video_type="video",
        audio_type="audio",
        subtitle_type="subtitle",
        track_id_key="track_id",
        mediainfo_width_key="width",
        mediainfo_height_key="height",
        mediainfo_bit_depth_key="bit_depth",
        matroska_extensions=(".mkv", ".mka", "mks"),
        matroska_video_extension=".mkv",
        matroska_audio_extension=".mka",
        matroska_subtitle_extension=".mks",
        mediainfo_video_type="Video",
        mediainfo_audio_type="Audio",
        mediainfo_subtitle_type="Text",
        mediainfo_track_id_key="streamorder",
        hevc_track_extension=".265",
        avc_track_extension=".264",
        mediainfo_colormatrix_key="matrix_coefficients",
        mediainfo_colorprim_key="color_primaries",
        mediainfo_transfer_key="transfer_characteristics",
        mediainfo_colormatrix_bt709="BT.709",
        mediainfo_colorprim_bt709="BT.709",
        mediainfo_transfer_bt709="BT.709",
        encoder_colormatrix_bt709="bt709",
        encoder_colorprim_bt709="bt709",
        encoder_transfer_bt709="bt709",
        vapoursynth_colormatrix_bt709="709",
        vapoursynth_colorprim_bt709="709",
        vapoursynth_transfer_bt709="709",
        fmtconv_colormatrix_bt709="709",
        fmtconv_colorprim_bt709="709",
        fmtconv_transfer_bt709="709",
        mediainfo_colormatrix_smpte170="BT.601",
        mediainfo_colorprim_smpte170="BT.601 NTSC",
        mediainfo_transfer_smpte170="BT.601",
        encoder_colormatrix_smpte170="smpte170m",
        encoder_colorprim_smpte170="smpte170m",
        encoder_transfer_smpte170="smpte170m",
        vapoursynth_colormatrix_smpte170="170m",
        vapoursynth_colorprim_smpte170="170m",
        vapoursynth_transfer_smpte170="601",
        fmtconv_colormatrix_smpte170="601",
        fmtconv_colorprim_smpte170="170m",
        fmtconv_transfer_smpte170="601",
        mediainfo_colormatrix_bt2020nc="BT.2020 non-constant",
        mediainfo_colormatrix_bt2020c="BT.2020 constant",
        mediainfo_colorprim_bt2020="BT.2020",
        mediainfo_colorprim_p3="Display P3",
        mediainfo_transfer_bt2020_10="BT.2020 (10-bit)",
        mediainfo_transfer_bt2020_12="BT.2020 (12-bit)",
        mediainfo_transfer_smpte2084="PQ",
        encoder_colormatrix_bt2020nc="bt2020nc",
        encoder_colormatrix_bt2020c="bt2020c",
        encoder_colorprim_bt2020="bt2020",
        encoder_colorprim_p3="p3",
        encoder_transfer_bt2020_10="bt2020-10",
        encoder_transfer_bt2020_12="bt2020-12",
        encoder_transfer_smpte2084="smpte2084",
        vapoursynth_colormatrix_bt2020nc="2020ncl",
        vapoursynth_colormatrix_bt2020c="2020cl",
        vapoursynth_colorprim_bt2020="2020",
        vapoursynth_transfer_bt2020_10="2020_10",
        vapoursynth_transfer_bt2020_12="2020_12",
        vapoursynth_transfer_smpte2084="st2084",
        fmtconv_colormatrix_bt2020nc="2020",
        fmtconv_colorprim_bt2020="2020",
        fmtconv_transfer_bt2020_10="2020_10",
        fmtconv_transfer_bt2020_12="2020_12",
        fmtconv_transfer_smpte2084="2084",
        fmtconv_colormatrix_rgb="rgb",
        fmtconv_colorprim_srgb="srgb",
        fmtconv_transfer_linear="linear",
        bt2020_available_bit_depth_tuple=(10, 12),
        encoder_max_cll_format_str="{max_content_light_level:.0f},{max_frameaverage_light_level:.0f}",
        encoder_master_display_prim_bt2020_format_str="G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L({max_master_display_luminance:.0f},{min_master_display_luminance:.0f})",
        encoder_master_display_prim_p3_format_str="G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L({max_master_display_luminance:.0f},{min_master_display_luminance:.0f})",
        mediainfo_mastering_display_luminance_re_exp="min: (?P<min>[\\d.]+?) cd/m2, max: (?P<max>[\\d.]+?) cd/m2",
        mediainfo_light_level_re_exp="(?P<num>[\\d.]+?) cd/m2",
    )

    constant_dict["mediainfo_encoder_colormatrix_dict"]: dict = {
        constant_dict["mediainfo_colormatrix_bt709"]: constant_dict[
            "encoder_colormatrix_bt709"
        ],
        constant_dict["mediainfo_colormatrix_smpte170"]: constant_dict[
            "encoder_colormatrix_smpte170"
        ],
        constant_dict["mediainfo_colormatrix_bt2020nc"]: constant_dict[
            "encoder_colormatrix_bt2020nc"
        ],
        constant_dict["mediainfo_colormatrix_bt2020c"]: constant_dict[
            "encoder_colormatrix_bt2020c"
        ],
    }
    constant_dict["mediainfo_encoder_colorprim_dict"]: dict = {
        constant_dict["mediainfo_colorprim_bt709"]: constant_dict[
            "encoder_colorprim_bt709"
        ],
        constant_dict["mediainfo_colorprim_smpte170"]: constant_dict[
            "encoder_colorprim_smpte170"
        ],
        constant_dict["mediainfo_colorprim_bt2020"]: constant_dict[
            "encoder_colorprim_bt2020"
        ],
        constant_dict["mediainfo_colorprim_p3"]: constant_dict[
            "encoder_colorprim_p3"
        ],
    }
    constant_dict["mediainfo_encoder_transfer_dict"]: dict = {
        constant_dict["mediainfo_transfer_bt709"]: constant_dict[
            "encoder_transfer_bt709"
        ],
        constant_dict["mediainfo_transfer_smpte170"]: constant_dict[
            "encoder_transfer_smpte170"
        ],
        constant_dict["mediainfo_transfer_bt2020_10"]: constant_dict[
            "encoder_transfer_bt2020_10"
        ],
        constant_dict["mediainfo_transfer_bt2020_12"]: constant_dict[
            "encoder_transfer_bt2020_12"
        ],
        constant_dict["mediainfo_transfer_smpte2084"]: constant_dict[
            "encoder_transfer_smpte2084"
        ],
    }

    constant_dict["encoder_fmtconv_colormatrix_dict"]: dict = {
        constant_dict["encoder_colormatrix_bt709"]: constant_dict[
            "fmtconv_colormatrix_bt709"
        ],
        constant_dict["encoder_colormatrix_smpte170"]: constant_dict[
            "fmtconv_colormatrix_smpte170"
        ],
        constant_dict["encoder_colormatrix_bt2020nc"]: constant_dict[
            "fmtconv_colormatrix_bt2020nc"
        ],
    }
    constant_dict["encoder_fmtconv_colorprim_dict"]: dict = {
        constant_dict["encoder_colorprim_bt709"]: constant_dict[
            "fmtconv_colorprim_bt709"
        ],
        constant_dict["encoder_colorprim_smpte170"]: constant_dict[
            "fmtconv_colorprim_smpte170"
        ],
        constant_dict["encoder_colorprim_bt2020"]: constant_dict[
            "fmtconv_colorprim_bt2020"
        ],
    }
    constant_dict["encoder_fmtconv_transfer_dict"]: dict = {
        constant_dict["encoder_transfer_bt709"]: constant_dict[
            "fmtconv_transfer_bt709"
        ],
        constant_dict["encoder_transfer_smpte170"]: constant_dict[
            "fmtconv_transfer_smpte170"
        ],
        constant_dict["encoder_transfer_bt2020_10"]: constant_dict[
            "fmtconv_transfer_bt2020_10"
        ],
        constant_dict["encoder_transfer_bt2020_12"]: constant_dict[
            "fmtconv_transfer_bt2020_12"
        ],
        constant_dict["encoder_transfer_smpte2084"]: constant_dict[
            "fmtconv_transfer_smpte2084"
        ],
    }

    constant_dict["encoder_colormatrix_transfer_dict"]: dict = {
        constant_dict["encoder_colormatrix_bt709"]: constant_dict[
            "encoder_transfer_bt709"
        ],
        constant_dict["encoder_colormatrix_smpte170"]: constant_dict[
            "encoder_transfer_smpte170"
        ],
        constant_dict["encoder_colormatrix_bt2020nc"]: constant_dict[
            "encoder_transfer_smpte2084"
        ],
        constant_dict["encoder_colormatrix_bt2020c"]: constant_dict[
            "encoder_transfer_smpte2084"
        ],
    }
    constant_dict["encoder_colormatrix_colorprim_dict"]: dict = {
        constant_dict["encoder_colormatrix_bt709"]: constant_dict[
            "encoder_colorprim_bt709"
        ],
        constant_dict["encoder_colormatrix_smpte170"]: constant_dict[
            "encoder_colorprim_smpte170"
        ],
        constant_dict["encoder_colormatrix_bt2020nc"]: constant_dict[
            "encoder_colorprim_bt2020"
        ],
        constant_dict["encoder_colormatrix_bt2020c"]: constant_dict[
            "encoder_colorprim_bt2020"
        ],
    }
    Constant: namedtuple = namedtuple("Constant", constant_dict.keys())
    constant: namedtuple = Constant(**constant_dict)
    return constant


