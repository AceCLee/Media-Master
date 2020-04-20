# Media Master

You transcode videos with your vapoursynth script template via Media Master.

If you want to transcode many videos with flexibility automatically, you should use it.

It supports series mission mode, you can transcode a series of videos, add audios, subtitles, chapters, attachments and so on.

It supports changing fps, changing sar, hdr, vfr and so on.

Chinese document: [Media Master - Ace的快乐屋](https://aceclee.com/archives/category/media-master)

Supported frameserver: VapourSynth.

Supported output video format: hevc([x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna), [NVEnc](https://github.com/rigaya/NVEnc)), avc([x264](https://github.com/jpsdr/x264), [NVEnc](https://github.com/rigaya/NVEnc)).

Supported output audio format: flac, opus, qaac.

Supported container: mkv, mp4.

## Table of Contents

- [Media Master](#media-master)
  - [Table of Contents](#table-of-contents)
  - [Background](#background)
  - [Install](#install)
  - [Usage](#usage)
  - [Badge](#badge)
  - [Related Efforts](#related-efforts)
  - [Maintainers](#maintainers)
  - [License](#license)

## Background

When I started to learn video transcoding, I just wanted to downscale some videos for my friend. I have found a software named MediaCoder, it is a great software, but it is too expensive to use it for me. So I started to develop a software to transcode many videos automatically.

Now, I can use Media Master to transcode videos expediently.

## Install

download Media Master

```shell
git clone https://github.com/AceCLee/Media-Master.git
```

install python library.

```shell
pip install -r requirements.txt
```

install [MKVToolNix Downloads](https://mkvtoolnix.download/downloads.html), [Downloads | GPAC](https://gpac.wp.imt.fr/downloads/), [NVEnc](https://github.com/rigaya/NVEnc), [x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna), [x264](https://github.com/jpsdr/x264), [msg7086/gop_muxer](https://github.com/msg7086/gop_muxer) and [Download FFmpeg](http://ffmpeg.org/download.html), after thar you need to add their paths to environment variables.

install [vapoursynth/vapoursynth: A video processing framework with simplicity in mind](https://github.com/vapoursynth/vapoursynth) and add path of vspipe.exe to environment variables.

## Usage

edit config files.

```shell
python compress.py
```

## Badge

[![GitHub](https://img.shields.io/github/license/AceCLee/Media-Master?style=flat-square)](https://github.com/AceCLee/Media-Master)

## Related Efforts

- [NVEnc](https://github.com/rigaya/NVEnc) - a cmdline tool to transcode videos with nvidia gpu and process videos.
- [x265-Yuuki-Asuna](https://github.com/msg7086/x265-Yuuki-Asuna) - a fork of x265 with more practical functions.

## Maintainers

[@AceCLee](https://github.com/AceCLee).

## License

[GPL-3.0](https://github.com/AceCLee/Media-Master/blob/master/LICENSE)