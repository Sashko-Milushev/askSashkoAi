from core.sanitize import sanitize


def test_strips_html_tags():
    assert sanitize("<b>hello</b>") == "hello"


def test_strips_script_block():
    assert sanitize('<script>alert("xss")</script>hello') == "hello"


def test_strips_style_block():
    assert sanitize("<style>body{color:red}</style>text") == "text"


def test_strips_control_chars():
    assert sanitize("hello\x00world") == "helloworld"


def test_preserves_newlines():
    result = sanitize("line1\nline2")
    assert "line1" in result and "line2" in result


def test_truncates_to_max_length():
    assert len(sanitize("a" * 100, max_length=10)) == 10


def test_strips_whitespace():
    assert sanitize("  hello  ") == "hello"


def test_empty_string():
    assert sanitize("") == ""

