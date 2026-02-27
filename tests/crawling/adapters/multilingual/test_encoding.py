"""Tests for multilingual encoding detection and conversion.

Validates:
    - Encoding detection from HTTP headers, meta charset, BOM, and chardet.
    - GB2312/GBK/GB18030 encoding normalization.
    - Shift_JIS/CP932 encoding normalization.
    - Windows-1256 encoding normalization.
    - Decode-with-fallback cascading chain.
    - Zero mojibake in converted output.
    - Script detection for CJK, Arabic, Hebrew, Cyrillic, Latin.
    - RTL mark stripping for Arabic/Hebrew mixed content.
    - Ruby annotation stripping for Japanese HTML.

Reference:
    Step 6 crawl-strategy-asia.md Section 8 (CJK Technical Notes).
    Step 3 research/crawling-feasibility.md (encoding analysis).
"""

from __future__ import annotations

import pytest

from src.crawling.adapters.multilingual._ml_utils import (
    detect_encoding,
    _extract_meta_charset,
    _normalize_encoding_name,
    decode_with_fallback,
    strip_rtl_marks,
    strip_ruby_annotations,
    detect_primary_script,
)


# ---------------------------------------------------------------------------
# Encoding detection
# ---------------------------------------------------------------------------


class TestEncodingDetection:
    """Test auto-detection of encoding from various sources."""

    def test_http_header_utf8(self):
        assert detect_encoding(b"hello", http_charset="utf-8") == "utf-8"

    def test_http_header_gb2312(self):
        assert detect_encoding(b"hello", http_charset="gb2312") == "gb18030"

    def test_http_header_shift_jis(self):
        assert detect_encoding(b"hello", http_charset="Shift_JIS") == "cp932"

    def test_http_header_windows_1256(self):
        assert detect_encoding(b"hello", http_charset="windows-1256") == "windows-1256"

    def test_meta_charset_gb2312(self):
        html = b'<html><head><meta charset="gb2312"></head>'
        assert detect_encoding(html) == "gb18030"

    def test_meta_charset_utf8(self):
        html = b'<html><head><meta charset="utf-8"></head>'
        assert detect_encoding(html) == "utf-8"

    def test_meta_charset_shift_jis(self):
        html = b'<html><head><meta charset="Shift_JIS"></head>'
        assert detect_encoding(html) == "cp932"

    def test_meta_http_equiv(self):
        html = b'<html><head><meta http-equiv="Content-Type" content="text/html; charset=gbk"></head>'
        assert detect_encoding(html) == "gb18030"

    def test_bom_utf8(self):
        raw = b"\xef\xbb\xbf<html>"
        assert detect_encoding(raw) == "utf-8"

    def test_bom_utf16(self):
        raw = b"\xff\xfe<\x00h\x00t\x00m\x00l\x00"
        assert detect_encoding(raw) == "utf-16"

    def test_default_no_hints(self):
        """When no encoding hints are found, chardet or UTF-8 fallback is used."""
        raw = b"<html><body>Hello</body></html>"
        result = detect_encoding(raw)
        # chardet may detect "ascii" for pure-ASCII content, which is a valid
        # superset of UTF-8. Both are acceptable for this content.
        assert result in ("utf-8", "ascii")

    def test_http_header_takes_priority(self):
        """HTTP header should override meta charset."""
        html = b'<html><head><meta charset="gb2312"></head>'
        result = detect_encoding(html, http_charset="utf-8")
        assert result == "utf-8"


# ---------------------------------------------------------------------------
# Meta charset extraction
# ---------------------------------------------------------------------------


class TestMetaCharsetExtraction:
    """Test _extract_meta_charset from raw bytes."""

    def test_meta_charset_tag(self):
        raw = b'<meta charset="gb2312">'
        assert _extract_meta_charset(raw) == "gb2312"

    def test_meta_charset_single_quotes(self):
        raw = b"<meta charset='utf-8'>"
        assert _extract_meta_charset(raw) == "utf-8"

    def test_meta_http_equiv(self):
        raw = b'<meta http-equiv="Content-Type" content="text/html; charset=gbk">'
        assert _extract_meta_charset(raw) == "gbk"

    def test_no_charset(self):
        raw = b"<html><head><title>Test</title></head>"
        assert _extract_meta_charset(raw) == ""


# ---------------------------------------------------------------------------
# Encoding normalization
# ---------------------------------------------------------------------------


class TestEncodingNormalization:
    """Test _normalize_encoding_name mapping."""

    @pytest.mark.parametrize("raw,expected", [
        ("gb2312", "gb18030"),
        ("gbk", "gb18030"),
        ("GB2312", "gb18030"),
        ("GBK", "gb18030"),
        ("gb18030", "gb18030"),
        ("Shift_JIS", "cp932"),
        ("shift_jis", "cp932"),
        ("sjis", "cp932"),
        ("cp932", "cp932"),
        ("euc-jp", "euc-jp"),
        ("EUC-JP", "euc-jp"),
        ("utf-8", "utf-8"),
        ("UTF-8", "utf-8"),
        ("windows-1256", "windows-1256"),
        ("iso-8859-1", "iso-8859-1"),
        ("latin1", "iso-8859-1"),
    ])
    def test_encoding_mapping(self, raw: str, expected: str):
        assert _normalize_encoding_name(raw) == expected

    def test_empty_returns_empty(self):
        assert _normalize_encoding_name("") == ""

    def test_unknown_passes_through(self):
        result = _normalize_encoding_name("some-unknown-enc")
        assert result == "some-unknown-enc"


# ---------------------------------------------------------------------------
# Decode with fallback
# ---------------------------------------------------------------------------


class TestDecodeWithFallback:
    """Test cascading encoding fallback chain."""

    def test_utf8_content(self):
        text = "\u4f60\u597d\u4e16\u754c"  # Chinese: "Hello World"
        raw = text.encode("utf-8")
        assert decode_with_fallback(raw) == text

    def test_gb18030_content(self):
        text = "\u4f60\u597d\u4e16\u754c"
        raw = text.encode("gb18030")
        result = decode_with_fallback(raw, primary_encoding="gb18030")
        assert result == text

    def test_gbk_content_via_gb18030(self):
        """GBK content should decode correctly via gb18030 superset."""
        text = "\u4f60\u597d\u4e16\u754c"
        raw = text.encode("gbk")
        result = decode_with_fallback(raw, primary_encoding="gb18030")
        assert result == text

    def test_shift_jis_content(self):
        text = "\u6771\u4eac\u90fd"  # Japanese: "Tokyo Metropolis"
        raw = text.encode("cp932")
        result = decode_with_fallback(raw, primary_encoding="cp932")
        assert result == text

    def test_euc_jp_content(self):
        text = "\u6771\u4eac\u90fd"
        raw = text.encode("euc-jp")
        result = decode_with_fallback(raw, primary_encoding="euc-jp")
        assert result == text

    def test_fallback_chain(self):
        """When primary encoding fails, fallback should succeed."""
        text = "\u6771\u4eac\u90fd"
        raw = text.encode("cp932")
        # Primary is utf-8 (wrong), fallback includes cp932
        result = decode_with_fallback(
            raw, primary_encoding="utf-8", fallback_encodings=["cp932"]
        )
        assert result == text

    def test_last_resort_utf8_replace(self):
        """When all encodings fail, return utf-8 with replacement."""
        raw = b"\x80\x81\x82\x83"  # Invalid UTF-8
        result = decode_with_fallback(raw)
        assert isinstance(result, str)

    def test_no_mojibake_chinese(self):
        """Verify no garbled text for Chinese content."""
        samples = [
            "\u4eba\u6c11\u65e5\u62a5",      # People's Daily
            "\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd",  # People's Republic of China
            "\u7ecf\u6d4e\u53d1\u5c55",      # Economic development
        ]
        for text in samples:
            for enc in ["utf-8", "gb18030", "gbk"]:
                raw = text.encode(enc)
                result = decode_with_fallback(raw, primary_encoding=enc)
                assert result == text, f"Mojibake for {text!r} with {enc}"

    def test_no_mojibake_japanese(self):
        """Verify no garbled text for Japanese content."""
        samples = [
            "\u6771\u4eac\u90fd",              # Tokyo
            "\u65e5\u672c\u8a9e\u30c6\u30b9\u30c8",  # Japanese test
            "\u8aad\u58f2\u65b0\u805e",        # Yomiuri Shimbun
        ]
        for text in samples:
            for enc in ["utf-8", "cp932", "euc-jp"]:
                raw = text.encode(enc)
                result = decode_with_fallback(raw, primary_encoding=enc)
                assert result == text, f"Mojibake for {text!r} with {enc}"

    def test_http_charset_hint(self):
        """HTTP charset hint should guide encoding detection."""
        text = "\u4f60\u597d"
        raw = text.encode("gb18030")
        result = decode_with_fallback(raw, http_charset="gb2312")
        assert result == text


# ---------------------------------------------------------------------------
# RTL mark stripping
# ---------------------------------------------------------------------------


class TestRTLStripping:
    """Test RTL/LTR directional mark removal."""

    def test_strip_rtl_mark(self):
        assert strip_rtl_marks("Hello\u200fWorld") == "HelloWorld"

    def test_strip_ltr_mark(self):
        assert strip_rtl_marks("Hello\u200eWorld") == "HelloWorld"

    def test_strip_arabic_letter_mark(self):
        assert strip_rtl_marks("Hello\u061cWorld") == "HelloWorld"

    def test_strip_zero_width_space(self):
        assert strip_rtl_marks("Hello\u200bWorld") == "HelloWorld"

    def test_strip_bom(self):
        assert strip_rtl_marks("\ufeffHello") == "Hello"

    def test_strip_multiple_marks(self):
        text = "\u200fArab\u200e \u061cNews\u200b Test\ufeff"
        expected = "Arab News Test"
        assert strip_rtl_marks(text) == expected

    def test_no_marks_unchanged(self):
        assert strip_rtl_marks("Hello World") == "Hello World"

    def test_empty_string(self):
        assert strip_rtl_marks("") == ""


# ---------------------------------------------------------------------------
# Ruby annotation stripping
# ---------------------------------------------------------------------------


class TestRubyStripping:
    """Test Japanese ruby/furigana annotation removal."""

    def test_basic_ruby(self):
        html = "<ruby>\u6771\u4eac<rt>\u3068\u3046\u304d\u3087\u3046</rt></ruby>"
        assert strip_ruby_annotations(html) == "\u6771\u4eac"

    def test_ruby_with_rp(self):
        html = "<ruby>\u6771\u4eac<rp>(</rp><rt>\u3068\u3046\u304d\u3087\u3046</rt><rp>)</rp></ruby>"
        assert strip_ruby_annotations(html) == "\u6771\u4eac"

    def test_ruby_preserves_base_text(self):
        html = "<ruby>\u6771\u4eac<rt>\u3068\u3046\u304d\u3087\u3046</rt></ruby>\u90fd"
        result = strip_ruby_annotations(html)
        assert "\u6771\u4eac" in result
        assert "\u90fd" in result
        assert "\u3068\u3046\u304d\u3087\u3046" not in result

    def test_multiple_ruby_elements(self):
        html = ("<ruby>\u6771<rt>\u3072\u304c\u3057</rt></ruby>"
                "<ruby>\u4eac<rt>\u304d\u3087\u3046</rt></ruby>")
        result = strip_ruby_annotations(html)
        assert "\u6771" in result
        assert "\u4eac" in result
        assert "\u3072\u304c\u3057" not in result
        assert "\u304d\u3087\u3046" not in result

    def test_no_ruby_unchanged(self):
        html = "<p>Normal paragraph without ruby.</p>"
        assert strip_ruby_annotations(html) == html


# ---------------------------------------------------------------------------
# Script detection
# ---------------------------------------------------------------------------


class TestScriptDetection:
    """Test primary script detection for routing to correct processing pipeline."""

    def test_cjk_chinese(self):
        assert detect_primary_script("\u4f60\u597d\u4e16\u754c\u8fd9\u662f\u4e2d\u6587\u6d4b\u8bd5") == "cjk"

    def test_cjk_japanese(self):
        assert detect_primary_script("\u6771\u4eac\u90fd\u5343\u4ee3\u7530\u533a\u5927\u624b\u753a") == "cjk"

    def test_cjk_hiragana(self):
        assert detect_primary_script("\u3053\u3093\u306b\u3061\u306f\u4e16\u754c\u3053\u308c\u306f\u30c6\u30b9\u30c8") == "cjk"

    def test_latin_english(self):
        assert detect_primary_script("Hello world this is a test string") == "latin"

    def test_latin_french(self):
        assert detect_primary_script("Bonjour le monde \u00e0 la fran\u00e7aise") == "latin"

    def test_latin_german(self):
        assert detect_primary_script("Guten Tag die Welt M\u00fcnchen \u00d6sterreich") == "latin"

    def test_cyrillic_russian(self):
        assert detect_primary_script("\u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440 \u044d\u0442\u043e \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442") == "cyrillic"

    def test_arabic(self):
        assert detect_primary_script("\u0645\u0631\u062d\u0628\u0627 \u0628\u0627\u0644\u0639\u0627\u0644\u0645 \u0647\u0630\u0627 \u0646\u0635 \u0639\u0631\u0628\u064a") == "arabic"

    def test_hebrew(self):
        assert detect_primary_script("\u05e9\u05dc\u05d5\u05dd \u05e2\u05d5\u05dc\u05dd \u05d8\u05e7\u05e1\u05d8 \u05e2\u05d1\u05e8\u05d9\u05ea") == "hebrew"

    def test_empty_unknown(self):
        assert detect_primary_script("") == "unknown"

    def test_short_unknown(self):
        assert detect_primary_script("abc") == "unknown"

    def test_numbers_only_unknown(self):
        assert detect_primary_script("12345 67890") == "unknown"
