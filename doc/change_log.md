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
