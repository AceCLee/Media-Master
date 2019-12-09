# Media Master

## Change Log

### Version 0.0.16.0

* 增加音频flac的压制功能
* 增加对输入格式为m2ts的支持
* 支持从能从MediaInfo获取章节信息的地方取得章节数据
* 修复指定最小GOP区间时的错误
* 修复若干错误

### Version 0.0.17.0

* 增加了日志系统中warning级别的日志输出
* 细分mkvmerge的返回值，根据返回值不同改变当下的行为
  * 之前的实现为只要不返回0，就会抛出错误，现在的实现为若返回1(mkvmerge输出警告)，程序继续运行，将在日志中记录警告，若返回2，抛出错误
* 配置文件中增加了audio_prior_option、external_audio_process_option、internal_audio_track_order_list、subtitle_prior_option、internal_subtitle_track_order_list四个选项，用于对于内外置音轨和内外置字幕更加细致的控制
* 修复若干错误

### Version 0.0.17.1

* 修复无法正确读取音频的错误

### Version 0.0.17.2

* 修复当输入文件不带有音频，但是指定了音频"transcode"或"copy"时会报的错误
* 在压制完成后的帧数校验时，比较帧数的时，优先获取MediaInfo中的"source_frame_count"字段中的帧率

### Version 0.0.17.3

* 修复内置音频只能压制一个的bug
* 修复外置音频和内置音频转码会冲突出现的bug

### Version 0.0.17.4

* x265的输出目录不接受非ascii字符，因此在每个压制任务之前预先将其中非ascii字符删除，输出文件名中的非ascii字符将会被删除。
