from datetime import date
import os
import re
from .rar_compress import rar_compress
import sys


def compress_log_expect_this_month(
    log_dir: str,
    rm_original=False,
    log_extension_re_exp="^\\.(\\d{4})-(\\d{2})-(\\d{2})$",
):
    re_pattern = re.compile(log_extension_re_exp)
    today_date = date.today()
    this_month = date(year=today_date.year, month=today_date.month, day=1)
    dict_key_format: str = "{year:0>4}-{month:0>2}"
    output_filename_format: str = "log-{datetime}"

    candidate_filepath_dict: dict = {}
    for full_filename in os.listdir(log_dir):
        filepath: str = os.path.join(log_dir, full_filename)
        filename, extension = os.path.splitext(full_filename)
        re_result = re.fullmatch(pattern=re_pattern, string=extension)
        if not re_result:
            continue
        year, month, day = (
            int(re_result.group(1)),
            int(re_result.group(2)),
            int(re_result.group(3)),
        )
        log_date = date(year=year, month=month, day=day)
        if log_date < this_month:
            log_dict_key: str = dict_key_format.format(year=year, month=month)
            if log_dict_key not in candidate_filepath_dict.keys():
                candidate_filepath_dict[log_dict_key] = {filepath}
            else:
                candidate_filepath_dict[log_dict_key].add(filepath)

    for date_str, filepath_set in candidate_filepath_dict.items():
        output_filename: str = output_filename_format.format(datetime=date_str)
        filename_set: set = set(
            os.path.basename(filepath) for filepath in filepath_set
        )
        rar_compress(
            input_filepath_set=filename_set,
            output_dir=log_dir,
            output_filename=output_filename,
            compress_level=5,
            solid_compress_bool=True,
            rar_version=4,
            text_compress_opt_bool=True,
            work_dir=log_dir,
        )
        if rm_original:
            for filepath in filepath_set:
                print(f"delete: {filepath}", file=sys.stderr)
                os.remove(filepath)


