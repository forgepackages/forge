from forge.logging import app_logger


def test_kv_format():
    assert app_logger.kv._format_value("1:thing") == '"1:thing"'
    assert app_logger.kv._format_value("") == '""'
