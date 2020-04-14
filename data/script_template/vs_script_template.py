import vapoursynth as vs
from vapoursynth import core

file_path = "{{input_filepath}}"

threads_num = {{threads_num}}
max_memory_size_mb = {{max_memory_size_mb}}

output_width = {{output_width}}
output_height = {{output_height}}

output_bit_depth = {{output_bit_depth}}
input_full_range_bool = {{input_full_range_bool}}

output_full_range_bool = {{output_full_range_bool}}

input_color_matrix = "{{input_color_matrix}}"

input_color_primaries = "{{input_color_primaries}}"

input_transfer = "{{input_transfer}}"

fps_num = {{fps_num}}
fps_den = {{fps_den}}

output_fps_num = {{output_fps_num}}
output_fps_den = {{output_fps_den}}

vfr_bool = {{vfr_bool}}

timecode_filepath = "{{timecode_filepath}}"


first_frame_index = {{first_frame_index}}
last_frame_index = {{last_frame_index}}


core.num_threads = threads_num
core.max_cache_size = max_memory_size_mb

if not vfr_bool:
    original: vs.VideoNode = core.lsmas.LWLibavSource(
        file_path, fpsnum=fps_num, fpsden=fps_den
    )
else:
    original: vs.VideoNode = core.lsmas.LWLibavSource(file_path)

original[first_frame_index:last_frame_index].set_output()
