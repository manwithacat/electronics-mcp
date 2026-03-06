import pytest
from electronics_mcp.core.units import parse_value, format_value


class TestParseValue:
    """Test EE unit string -> float conversion."""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            # SI prefix shorthand
            ("100", 100.0),
            ("10k", 10_000.0),
            ("4.7k", 4_700.0),
            ("47u", 47e-6),
            ("10n", 10e-9),
            ("100p", 100e-12),
            ("2.2m", 2.2e-3),
            ("1M", 1e6),
            # Explicit units
            ("10kohm", 10_000.0),
            ("100nF", 100e-9),
            ("2.2mH", 2.2e-3),
            ("1uA", 1e-6),
            ("3.3V", 3.3),
            ("47uF", 47e-6),
            # Edge cases
            ("0", 0.0),
            ("0V", 0.0),
            ("1", 1.0),
        ],
    )
    def test_parse_value(self, input_str, expected):
        result = parse_value(input_str)
        assert abs(result - expected) < expected * 1e-9 + 1e-15


class TestFormatValue:
    """Test float -> EE unit string conversion."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (10_000.0, "10k"),
            (47e-6, "47u"),
            (100e-9, "100n"),
            (2.2e-3, "2.2m"),
            (1e6, "1M"),
            (100.0, "100"),
            (100e-12, "100p"),
        ],
    )
    def test_format_value(self, value, expected):
        assert format_value(value) == expected
