from iso639 import languages


def all_iso639_code_set():
    all_code_set: set = set()

    all_code_set |= set(la.part1 for la in languages)
    all_code_set |= set(la.part2t for la in languages)
    all_code_set |= set(la.part2b for la in languages)
    all_code_set |= set(la.part3 for la in languages)
    all_code_set |= set(la.part5 for la in languages)

    all_code_set.remove("")

    return all_code_set


