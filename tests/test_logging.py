from forge.logging import app_logger


def test_kv_format():
    s = "1:thing"
    assert app_logger.kv._format_value(s) == '"1:thing"'
