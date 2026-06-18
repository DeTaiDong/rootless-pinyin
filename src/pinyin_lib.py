"""ctypes bindings for the system libpinyin.so, used to back a user-level IBus engine.

Function signatures come from libpinyin's public C API (src/pinyin.h in the
libpinyin source tree); the option bitmask values come from pinyin_custom2.h.
"""

import ctypes
import ctypes.util
import os
from ctypes import (
    c_char_p, c_void_p, c_int, c_uint, c_uint8, c_size_t, c_bool,
    POINTER, byref, cast,
)

LIBPINYIN_CANDIDATES = (
    "/usr/lib64/libpinyin.so.13",
    "/usr/lib/libpinyin.so.13",
    "/usr/lib/x86_64-linux-gnu/libpinyin.so.13",
)
DATA_DIR_CANDIDATES = (
    "/usr/lib64/libpinyin/data",
    "/usr/lib/libpinyin/data",
    "/usr/lib/x86_64-linux-gnu/libpinyin/data",
    "/usr/share/libpinyin/data",
)


def _first_existing_path(env_name, candidates, is_dir=False):
    configured = os.environ.get(env_name)
    if configured:
        exists = os.path.isdir(configured) if is_dir else os.path.exists(configured)
        if exists:
            return configured
        raise RuntimeError("%s points to a missing path: %s" % (env_name, configured))

    for path in candidates:
        exists = os.path.isdir(path) if is_dir else os.path.exists(path)
        if exists:
            return path
    return None


def _find_libpinyin():
    path = _first_existing_path("LIBPINYIN_PATH", LIBPINYIN_CANDIDATES)
    if path:
        return path
    found = ctypes.util.find_library("pinyin")
    if found:
        return found
    raise RuntimeError(
        "Could not find libpinyin. Set LIBPINYIN_PATH to the libpinyin shared library."
    )


def _find_data_dir():
    path = _first_existing_path("LIBPINYIN_DATA_DIR", DATA_DIR_CANDIDATES, is_dir=True)
    if path:
        return path
    raise RuntimeError(
        "Could not find libpinyin data. Set LIBPINYIN_DATA_DIR to the data directory."
    )


LIBPINYIN_PATH = _find_libpinyin()
SYSTEM_DATA_DIR = _find_data_dir()

IS_PINYIN = 1 << 1
PINYIN_INCOMPLETE = 1 << 3
USE_TONE = 1 << 5
USE_DIVIDED_TABLE = 1 << 7
USE_RESPLIT_TABLE = 1 << 8
DYNAMIC_ADJUST = 1 << 9
PINYIN_CORRECT_ALL = 0xFF << 21
DEFAULT_OPTIONS = (
    IS_PINYIN | PINYIN_INCOMPLETE | USE_TONE | USE_DIVIDED_TABLE
    | USE_RESPLIT_TABLE | DYNAMIC_ADJUST | PINYIN_CORRECT_ALL
)

SORT_BY_PHRASE_LENGTH_AND_FREQUENCY = 1

_lib = ctypes.CDLL(LIBPINYIN_PATH)
_glib = ctypes.CDLL("libglib-2.0.so.0")
_glib.g_free.argtypes = [c_void_p]
_glib.g_free.restype = None

_lib.pinyin_init.argtypes = [c_char_p, c_char_p]
_lib.pinyin_init.restype = c_void_p
_lib.pinyin_set_options.argtypes = [c_void_p, c_uint]
_lib.pinyin_set_options.restype = c_bool
_lib.pinyin_alloc_instance.argtypes = [c_void_p]
_lib.pinyin_alloc_instance.restype = c_void_p
_lib.pinyin_free_instance.argtypes = [c_void_p]
_lib.pinyin_free_instance.restype = None
_lib.pinyin_fini.argtypes = [c_void_p]
_lib.pinyin_fini.restype = None
_lib.pinyin_save.argtypes = [c_void_p]
_lib.pinyin_save.restype = c_bool

_lib.pinyin_parse_more_full_pinyins.argtypes = [c_void_p, c_char_p]
_lib.pinyin_parse_more_full_pinyins.restype = c_size_t
_lib.pinyin_get_parsed_input_length.argtypes = [c_void_p]
_lib.pinyin_get_parsed_input_length.restype = c_size_t

_lib.pinyin_guess_sentence.argtypes = [c_void_p]
_lib.pinyin_guess_sentence.restype = c_bool
_lib.pinyin_get_sentence.argtypes = [c_void_p, c_uint8, POINTER(c_char_p)]
_lib.pinyin_get_sentence.restype = c_bool

_lib.pinyin_guess_candidates.argtypes = [c_void_p, c_size_t, c_int]
_lib.pinyin_guess_candidates.restype = c_bool
_lib.pinyin_get_n_candidate.argtypes = [c_void_p, POINTER(c_uint)]
_lib.pinyin_get_n_candidate.restype = c_bool
_lib.pinyin_get_candidate.argtypes = [c_void_p, c_uint, POINTER(c_void_p)]
_lib.pinyin_get_candidate.restype = c_bool
_lib.pinyin_get_candidate_string.argtypes = [c_void_p, c_void_p, POINTER(c_char_p)]
_lib.pinyin_get_candidate_string.restype = c_bool
_lib.pinyin_choose_candidate.argtypes = [c_void_p, c_size_t, c_void_p]
_lib.pinyin_choose_candidate.restype = c_int

_lib.pinyin_train.argtypes = [c_void_p, c_uint8]
_lib.pinyin_train.restype = c_bool
_lib.pinyin_reset.argtypes = [c_void_p]
_lib.pinyin_reset.restype = c_bool


class PinyinSession(object):
    """One pinyin_context_t + pinyin_instance_t pair, with a pythonic API."""

    def __init__(self, user_dir):
        self._context = _lib.pinyin_init(
            SYSTEM_DATA_DIR.encode("utf-8"), user_dir.encode("utf-8")
        )
        if not self._context:
            raise RuntimeError("pinyin_init failed (system data dir missing?)")
        _lib.pinyin_set_options(self._context, DEFAULT_OPTIONS)
        self._instance = _lib.pinyin_alloc_instance(self._context)
        if not self._instance:
            _lib.pinyin_fini(self._context)
            self._context = None
            raise RuntimeError("pinyin_alloc_instance failed")

    def parse(self, raw_pinyin):
        _lib.pinyin_reset(self._instance)
        n = _lib.pinyin_parse_more_full_pinyins(self._instance, raw_pinyin.encode("ascii"))
        _lib.pinyin_guess_sentence(self._instance)
        return n

    def parsed_length(self):
        return _lib.pinyin_get_parsed_input_length(self._instance)

    def best_sentence(self):
        out = c_char_p()
        ok = _lib.pinyin_get_sentence(self._instance, 0, byref(out))
        if not ok or not out.value:
            return ""
        text = out.value.decode("utf-8")
        _glib.g_free(cast(out, c_void_p))
        return text

    def candidates(self, offset, limit=9):
        if not _lib.pinyin_guess_candidates(
            self._instance, offset, SORT_BY_PHRASE_LENGTH_AND_FREQUENCY
        ):
            return []
        n = c_uint(0)
        if not _lib.pinyin_get_n_candidate(self._instance, byref(n)):
            return []
        out = []
        for i in range(min(n.value, limit)):
            cand_ptr = c_void_p()
            if not _lib.pinyin_get_candidate(self._instance, i, byref(cand_ptr)):
                continue
            s = c_char_p()
            if not _lib.pinyin_get_candidate_string(self._instance, cand_ptr, byref(s)):
                continue
            text = s.value.decode("utf-8") if s.value else ""
            # Candidate strings are owned by libpinyin on some releases.
            out.append((text, cand_ptr))
        return out

    def choose(self, offset, cand_ptr):
        return _lib.pinyin_choose_candidate(self._instance, offset, cand_ptr)

    def train(self):
        _lib.pinyin_train(self._instance, 0)

    def reset(self):
        _lib.pinyin_reset(self._instance)

    def save(self):
        if self._context:
            _lib.pinyin_save(self._context)

    def close(self):
        if self._instance:
            _lib.pinyin_free_instance(self._instance)
            self._instance = None
        if self._context:
            _lib.pinyin_fini(self._context)
            self._context = None
