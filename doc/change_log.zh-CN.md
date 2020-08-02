# Media Master

## Change Log

### Version 0.0.10.0

* 将video.transcode.transcode_video_x265中存储stderror的信息的实现更改：
原实现：将每行的信息都存在一个字符串中，每读取指定行数清空一次字符串。
注解：虽然保证了字符串不会有超过指定行数的数据，但是并不能保证有尽可能多的信息，甚至可能需要的信息刚好在输出之前被清空了。
新实现：使用队列存储指定行数的stderr信息，元素为每行stderr的字符串。使用collections.deque。
注解：保证不论在何处结束都能输出指定函数的stderr信息。

### Version 0.0.10.1

* 修复Version 0.0.10.0的队列存储指定行数的stderr信息的BUG：
原实现：使用队列存储指定行数的stderr信息，元素为每行stderr的字符串。但是即使读取到的每行信息为空，也会加入队列。
注解：很有可能出现队列里面全是空字符串。
新实现：先判断该行字符串是否为空，再加入队列中。
注解：保证不会存储无效的stderr信息。

### Version 0.0.10.2

* 将media_master.transcode全部变为面向对象实现：
原实现：面向过程实现。
注解：不容易模块化。
新实现：面向对象实现。
注解：容易模块化，但是还未实现参数检查部分。

* 将media_master.video.transcode的x265和nvenc变为面向对象实现，并且加入了x264的压制：
原实现：面向过程实现。
注解：大量代码冗余重复。
新实现：面向对象实现。
注解：使用继承重复利用代码，后面考虑使用多重继承复用代码。

* 更改了VS脚本，加入了新的模板参数"video_style"
* 更改了多处配置文件的，使其更加规范统一化

### Version 0.0.10.3

* 加入添加附件功能
* single支持添加多个字幕

### Version 0.0.10.4

* 为字幕轨加上标题和语言

### Version 0.0.10.5

* 将fps的赋值由纯数字改为"分子/分母"的形式

### Version 0.0.11.0

* 使用统一标准的配置文件格式
* 支持指定任何轨道的title和language
* 支持系列多字幕
* 支持多音轨转码

### Version 0.0.11.1

* 加入qaac音频编码

### Version 0.0.11.2

* 加入视频和音频压制复用的功能

### Version 0.0.11.3

* 自动生成顺序和逆序的集数的功能
* 修复外置音频的BUG，之前版本的外置音频是全局配置，也就是说即使对于series，不能按照集数的正则表达式配置
* 复制视频轨道时，不再将视频提取出来(--repeat-header参数压制的流，被提取出来时一开始会出现绿屏)

### Version 0.0.11.4

* 章节信息的分集指定

### Version 0.0.12.0

* 使用GOP分段压制，支持断点续压
* 由于使用Asuna版本的x265，自带较为全面的命令行输出，未修改之前x265正则表达式判定和输出。

### Version 0.0.12.1

* 对分GOP压制的脚本名称进行了改进
* 针对Asuna版本的x265修改之前x265正则表达式判定和输出
* 为了保证正常的命令行输出，即使用户输入了--stylish参数，也会被去除

### Version 0.0.13.0

* 支持按章节分段制定压制脚本和压制参数

### Version 0.0.13.1

* 增加x265中压制详细压制信息(总帧数、时间、压制FPS、比特率、平均QP)打印和输出日志的功能

### Version 0.0.13.2

* 增加提取视频和音频时若输出文件已经存在，就跳过的功能，减少大体积视频和音频对固态硬盘的损耗

### Version 0.0.14.0

* 加入逐帧分析输入视频，并根据gop码率改变压制参数的功能。
* 修复分段配置GOP压制时，预先配置两个的GOP叠在一起，无法生成正确最终配置的BUG。

### Version 0.0.14.1

* 当压制视频和源视频标注的总帧数不同时，差别小于3时，会留下警告，差别不小于3时，会抛出错误
* 增加若干gop分析的功能

### Version 0.0.14.2

* 修复了GOP信息空输入的情况下的BUG

### Version 0.0.14.3

* 为了兼容从mkv提取流会出错的视频，将提取流改变为复制原视频整体

### Version 0.0.14.4

* 修复分段参数压制失效的BUG
* 修复正则表达式找不到任何文件但是不报错的BUG

### Version 0.0.14.5

* 发现在某些特殊的源，例如reinforce的未确认进行式的OAD，会出现mediainfo读不出总帧数的问题，读不出总帧数就相当于分段压制不可能实现，因此遇到不能读取总帧数的源，先用最新版的mkvmerge封装一次，就可以读取总帧数。

### Version 0.0.14.6

* 加入当Gop区间过多抛出错误的功能，加入预测gop_muxer命令行参数长度的功能并输出至stderr
注解：由于Gop区间过于分散，在剧场版的压制时，在gop_muxer的封装部分，会出现Windows命令行参数无法正确接受过长的命令行参数的无解错误。后续考虑更换gop_muxer的调用目录，使用相对路径进行尝试。

### Version 0.0.14.7

* 加入识别音频中mp2音频，正确输出音频后缀的功能
* 修复GopX265VspipeVideoTranscoding中封装错误的Bug

### Version 0.0.14.8

* 在frame_server_template_config中，增加了"{{input_video_width}}"、"{{input_video_height}}"、"{{2x_input_video_width}}"、"{{2x_input_video_height}}"、"{{4x_input_video_width}}"、"{{4x_input_video_height}}"模板

### Version 0.0.14.9

* 加入识别音频中pcm音频，正确输出音频后缀的功能

### Version 0.0.14.10

* 加入对非264、265视频流使用mkv重新封装，得到正确的帧率和帧数的功能

### Version 0.0.15.0

* 加入自动化转码BD中音频和图片的功能
* 加入由同一个single配置生成多个不同路径但是参数相同的配置模板功能

### Version 0.0.15.1

* 小错误的修复

### Version 0.0.15.2

* 在x265分GOP压制时，将缓存文件名映射为短长度hash，压缩缓存文件长度，完善超出长度提醒功能

### Version 0.0.15.3

* 封装和完善了对不可信任的视频元数据的判断

### Version 0.0.15.4

* 修复小错误，发布前最后一版本

### Version 0.0.15.5

* 删除和修改一些注释
* 将encapsulation和encapsulate改名为multiplex

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

### Version 0.0.17.5

* 增加压缩日志之功能

### Version 0.0.17.6

* 对输入mkv有章节但是没有章节信息时出现的bug进行修复
* 加入分析无效ass字幕的功能

### Version 0.0.17.7

* 加入根据MediaInfo信息更改文件名的功能

### Version 0.0.17.8

* 加入自动生成x265转码参数模板的功能

### Version 0.0.17.9

* 修正hash相关模块的接口的参数名称
* 考虑到输出帧率模式一般为cfr，增加对输入为vfr模式的视频的支持，自动将帧率和帧数改为cfr模式下的帧率
* 增加对vspipe+nvenc模式的支持
* 增加在最后混流时指定视频的帧率的功能，视频信息中增加fps的键值对即可实现
* 增加对Voukoder封装的mkv的meta_data的信任
* 修复了multiplex模块在校验是否所有键都存在的错误

### Version 0.0.18.0

* 增加封装为mp4格式的功能
* 在get_proper_frame_rate中增加讲23976/1000和29970/1000标准化的功能
* 加入配置中单独指定转码参数的模板键值对功能

### Version 0.0.18.1

* 外置音频和外置字幕可以直接从容器文件的轨道中提取
* mkvextract增加对mka文件的支持
* nvenc在读取新版本的mkv容器会无故闪退，因此在使用nvenc选择将视频流提取出来作为nvenc的输入

### Version 0.0.18.2

* 修复整数倍帧数在LWLibavSource出现的错误
* 修复track_index_list的相关bug

### Version 0.0.18.3

* 若mkvextract提取主要流出现了警告，但是extract仍然进行了，此时不会报错，但是会在日志中留下warning
* 修复无法提取vobsub为idx格式的字幕的错误
* 若mkvextract提取附件和章节的该错误没有修复
* 增加指定输出帧率的功能
* 将在封装mkv时指定帧率的功能消除
* 将在封装mp4时指定帧率的功能消除
* nvenc的输入文件变为整个原视频容器
* 去除帧数检测功能

### Version 0.0.18.4

* 加入多线程并行转码视频和音轨的功能，但是输出会变得很乱
* 去除字幕、音频和视频的个数必须匹配的限制
* aac文件作为中间缓存文件时，直接保存aac文件无法保存时长信息，将其改为m4a封装的aac格式，防止出现时长错误
* 修复封装mp4无法复制视频流的bug
* 当输入文件路径长度大于255时，自动复制至缓存文件夹处理
* 暂时将视频源元数据无法信任时封装的mkv格式的视频流的延迟全归零(nvenc字幕受到延迟影响bug)

### Version 0.0.18.5

* 加入对mp4封装章节的支持
* 针对mp4box不能正确视频路径的bug[MP4Box: Import options which have colons in them not properly parsed · Issue #873 · gpac/gpac](https://github.com/gpac/gpac/issues/873#issuecomment-521693709)，将路径变为标准化路径避免bug
* 修复封装mp4并且复制视频流时不会自动删除视频中间缓存文件的bug

### Version 0.0.18.6

* 将视频源元数据无法信任时封装的mkv格式的视频流的延迟全归零去除
* 增加脚本模板"{{output_fps_num}}","{{output_fps_den}}"，该值为配置文件中"output_fps"指定的输出
* 暂时去除将输出文件不可打印字符去除的功能
* 输入文件为vob封装时，预先封装为mkv
* 将x264的转码匹配最新版的[x264 tmod](https://github.com/jpsdr/x264/releases)
* 加入更改内置音轨时延的功能
* 修复了mp4提取流时出现的空的流序号的错误
* 修复不指定视频转码参数模板时出现的bug
* 由于较新版的MP4BOX封装的视频，不会直接在容器的音频轨道的元信息中留下delay_ms的信息，所以将所有mp4进行预封装
* 修复复制视频时，无法指定输出视频元信息的bug
* 修复了当通过"output_fps"更改输出帧率时，x265在分段压制时，

### Version 0.0.18.7

* 增加对输出文件名的非ASCII字符的支持，某些编码器不支持非ASCII字符，之前中间缓存文件名均使用输出文件名，可能会报错。修改：中间缓存文件名为原文件删去非可见字符+哈希。
* 输入文件扩展名为mpls,m2ts,vob,mp4会进行预封装为mkv
* 将多线程模式改为：字幕操作、章节操作和附件操作串行，后为视频操作和音频操作有条件地并行(错开io)，错开所有操作的io，防止因io操作过于密集造成错误出现。
* 增加对wmv和wma格式的支持

### Version 0.0.18.8

* 所有视频都预封装为mkv格式
* 增加对vfr的支持
* 增加对sar压制的支持

### Version 0.0.18.9

* 增加对hdr压制的支持
* 修复若干小错误

### Version 0.0.19.0

* 压制前对配置文件绝大多数值进行正确性检查

### Version 0.0.19.1

* 将修改元信息的实现从mkvmerge改为mkvpropedit

### Version 0.0.19.2

* 修复正确性检查在copy视频时的一个逻辑错误
* 修复视频提取和音频提取IO操作未错开的错误
* 针对x264在中断压制后又重新压制导致和一次成型时体积的巨大差异，尝试通过在压制前删除之前的.264文件来避免此问题
* 在正确性检查中加入将字幕非uft-8-bom编码更改为uft-8-bom编码，以应对vsmod无法识别uft-8编码的问题
* mkvmerge在封装mkv文件时，媒体轨道原来的延迟会被考虑在内，不需要单独指定，不然会重复指定，修复之前版本会重复指定的错误
* 在预检查中，增加对frame_server_template_config内的字幕文件的字体检查功能

### Version 0.0.19.3

* 检查硬字幕字体即"frame_server_template_config"-"subtitle_filepath"中字幕的字体是否存在(Windows Only)
* 修复转码后未将视频流索引置为0(仍然为输入视频容器的视频轨的索引)的错误
* 修复压制视频之前未检查编码器环境变量的问题
* 在调用子进程时，为了避免出现UnicodeDecodeError，调用子进程加入errors参数以规避该错误
* 将universal_config改为general_config

### Version 0.0.19.4

* 在配置文件中加入硬字幕读取功能，并作为模板{{hardcoded_subtitle_filepath}}给出
* 增加了硬字幕的字型检查功能，可允许的缺失字型由"global_config.json"中的"subtitle_allowable_missing_glyph_char_list"给出
* 完善了series转码的预检查逻辑
* 优化了缓存文件的文件名
