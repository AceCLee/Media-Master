from ..error import RangeError


def resort(src, order_list):
    if len(order_list) > len(src):
        raise ValueError(
            f"len(order_list) > len(src) {len(order_list)} > {len(src)}"
        )
    if any(index not in order_list for index in range(len(order_list))):
        RangeError(
            message=(
                f"index of src must be in {list(range(len(order_list)))}"
            ),
            valid_range=str(list(range(len(order_list)))),
        )
    if len(order_list) < len(src):
        order_list += list(range(len(order_list), len(src)))
    return sorted(src, key=lambda x: order_list[src.index(x)])


