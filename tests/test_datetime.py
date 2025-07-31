"""
Comprehensive datetime handling tests for CEL bindings.

This module consolidates all datetime-related testing including:
- Timezone handling and conversion
- Edge cases and error conditions
- Arithmetic operations
- Type preservation and robustness
"""

import datetime

import cel
import pytest


class TestDatetimeBasics:
    """Test basic datetime functionality and type handling."""

    def test_datetime_with_different_timezones(self):
        """Test datetime handling with various timezone configurations."""

        # UTC timezone
        utc_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": utc_time})
        assert result == utc_time
        assert result.tzinfo == datetime.timezone.utc

        # Fixed offset timezone (+5 hours)
        offset_tz = datetime.timezone(datetime.timedelta(hours=5))
        offset_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=offset_tz)
        result = cel.evaluate("dt", {"dt": offset_time})
        assert result == offset_time
        assert result.tzinfo == offset_tz

        # Fixed offset timezone (-8 hours)
        negative_offset_tz = datetime.timezone(datetime.timedelta(hours=-8))
        negative_offset_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=negative_offset_tz)
        result = cel.evaluate("dt", {"dt": negative_offset_time})
        assert result == negative_offset_time
        assert result.tzinfo == negative_offset_tz

    def test_naive_datetime_conversion(self):
        """Test that naive datetimes are properly converted to timezone-aware."""
        naive_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = cel.evaluate("dt", {"dt": naive_time})

        # Should convert to timezone-aware datetime
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None

        # The local time conversion should preserve the time value in local context
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0

    def test_datetime_microseconds(self):
        """Test that microseconds are preserved in datetime conversion."""
        dt_with_microseconds = datetime.datetime(
            2024, 1, 1, 12, 0, 0, 123456, tzinfo=datetime.timezone.utc
        )
        result = cel.evaluate("dt", {"dt": dt_with_microseconds})
        assert result == dt_with_microseconds
        assert result.microsecond == 123456

    def test_datetime_type_consistency(self):
        """Test that datetime types remain consistent through CEL operations."""
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        delta = datetime.timedelta(hours=1)

        # Verify types are preserved
        dt_result = cel.evaluate("dt", {"dt": dt})
        assert isinstance(dt_result, datetime.datetime)

        delta_result = cel.evaluate("delta", {"delta": delta})
        assert isinstance(delta_result, datetime.timedelta)

        # Arithmetic should return correct types
        add_result = cel.evaluate("dt + delta", {"dt": dt, "delta": delta})
        assert isinstance(add_result, datetime.datetime)


class TestDatetimeArithmetic:
    """Test datetime arithmetic operations."""

    def test_datetime_arithmetic(self):
        """Test datetime arithmetic operations."""
        base_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        one_hour = datetime.timedelta(hours=1)

        # Test datetime addition
        result = cel.evaluate("dt + duration", {"dt": base_time, "duration": one_hour})
        expected = base_time + one_hour
        assert result == expected

        # Test datetime subtraction
        result = cel.evaluate("dt - duration", {"dt": base_time, "duration": one_hour})
        expected = base_time - one_hour
        assert result == expected

    def test_datetime_arithmetic_edge_cases(self):
        """Test edge cases in datetime arithmetic."""
        base_dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Add zero duration
        zero_delta = datetime.timedelta(0)
        result = cel.evaluate("dt + delta", {"dt": base_dt, "delta": zero_delta})
        assert result == base_dt

        # Subtract zero duration
        result = cel.evaluate("dt - delta", {"dt": base_dt, "delta": zero_delta})
        assert result == base_dt

    def test_nested_datetime_operations(self):
        """Test datetime operations in nested expressions."""
        dt1 = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        dt2 = datetime.datetime(2024, 1, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)
        delta = datetime.timedelta(hours=1)

        context = {"dt1": dt1, "dt2": dt2, "delta": delta}

        # Complex datetime expression
        result = cel.evaluate("(dt1 + delta) == dt2", context)
        assert result is True

        # Nested comparison
        result = cel.evaluate("dt1 < dt2 && (dt1 + delta) == dt2", context)
        assert result is True


class TestDatetimeComparisons:
    """Test datetime comparison operations."""

    def test_datetime_comparisons(self):
        """Test datetime comparison operations."""
        dt1 = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        dt2 = datetime.datetime(2024, 1, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)

        # dt1 < dt2
        result = cel.evaluate("dt1 < dt2", {"dt1": dt1, "dt2": dt2})
        assert result is True

        # dt1 == dt1
        result = cel.evaluate("dt1 == dt1", {"dt1": dt1})
        assert result is True

        # dt2 > dt1
        result = cel.evaluate("dt2 > dt1", {"dt1": dt1, "dt2": dt2})
        assert result is True

    def test_timezone_awareness_mixed(self):
        """Test mixing timezone-aware and naive datetimes."""
        utc_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        naive_time = datetime.datetime(2024, 1, 1, 12, 0, 0)

        context = {"utc_dt": utc_time, "naive_dt": naive_time}

        # Both should be accessible
        result_utc = cel.evaluate("utc_dt", context)
        assert result_utc == utc_time

        result_naive = cel.evaluate("naive_dt", context)
        assert isinstance(result_naive, datetime.datetime)
        assert result_naive.tzinfo is not None  # Should be converted to timezone-aware


class TestTimedelta:
    """Test timedelta handling and operations."""

    def test_timedelta_operations(self):
        """Test timedelta handling and operations."""

        # Various timedelta units
        microseconds_delta = datetime.timedelta(microseconds=123456)
        result = cel.evaluate("delta", {"delta": microseconds_delta})
        assert result == microseconds_delta

        seconds_delta = datetime.timedelta(seconds=45)
        result = cel.evaluate("delta", {"delta": seconds_delta})
        assert result == seconds_delta

        minutes_delta = datetime.timedelta(minutes=30)
        result = cel.evaluate("delta", {"delta": minutes_delta})
        assert result == minutes_delta

        hours_delta = datetime.timedelta(hours=6)
        result = cel.evaluate("delta", {"delta": hours_delta})
        assert result == hours_delta

        days_delta = datetime.timedelta(days=7)
        result = cel.evaluate("delta", {"delta": days_delta})
        assert result == days_delta

        weeks_delta = datetime.timedelta(weeks=2)
        result = cel.evaluate("delta", {"delta": weeks_delta})
        assert result == weeks_delta

    def test_timedelta_edge_cases(self):
        """Test edge cases for timedelta handling."""

        # Maximum timedelta
        max_delta = datetime.timedelta(days=999999999, seconds=86399, microseconds=999999)
        result = cel.evaluate("delta", {"delta": max_delta})
        assert result == max_delta

        # Minimum (negative) timedelta
        min_delta = datetime.timedelta(days=-999999999)
        result = cel.evaluate("delta", {"delta": min_delta})
        assert result == min_delta

        # Zero timedelta
        zero_delta = datetime.timedelta(0)
        result = cel.evaluate("delta", {"delta": zero_delta})
        assert result == zero_delta


class TestDatetimeEdgeCases:
    """Test edge cases and error conditions for datetime operations."""

    def test_datetime_edge_cases(self):
        """Test edge cases in datetime handling."""

        # Year 1 (minimum year)
        min_dt = datetime.datetime(1, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": min_dt})
        assert result == min_dt

        # Year 9999 (maximum year)
        max_dt = datetime.datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": max_dt})
        assert result == max_dt

        # Leap year February 29th
        leap_dt = datetime.datetime(2024, 2, 29, 12, 0, 0, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": leap_dt})
        assert result == leap_dt

    def test_datetime_near_epoch(self):
        """Test datetime values near Unix epoch."""
        # Unix epoch start
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": epoch})
        assert result == epoch

        # Just before epoch
        pre_epoch = datetime.datetime(1969, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": pre_epoch})
        assert result == pre_epoch

    def test_datetime_with_extreme_microseconds(self):
        """Test datetime with maximum microseconds."""
        extreme_dt = datetime.datetime(2024, 1, 1, 12, 0, 0, 999999, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": extreme_dt})
        assert result == extreme_dt
        assert result.microsecond == 999999

    def test_datetime_string_representations(self):
        """Test that datetime objects maintain their properties through conversion."""
        dt = datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.timezone.utc)

        # Pass through CEL evaluation
        result = cel.evaluate("dt", {"dt": dt})

        # Verify all components are preserved
        assert result.year == dt.year
        assert result.month == dt.month
        assert result.day == dt.day
        assert result.hour == dt.hour
        assert result.minute == dt.minute
        assert result.second == dt.second
        assert result.microsecond == dt.microsecond
        assert result.tzinfo == dt.tzinfo

    def test_ambiguous_local_datetime(self):
        """Test handling of ambiguous local datetime during DST transitions."""

        # Create a naive datetime that would be ambiguous during DST transition
        # This is tricky to test without specific timezone libraries
        # but we can test the error handling path

        # For now, test with a normal naive datetime to ensure the conversion works
        naive_dt = datetime.datetime(2024, 1, 1, 2, 30, 0)  # No DST ambiguity in January
        result = cel.evaluate("dt", {"dt": naive_dt})
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None

    def test_dst_transition_dates(self):
        """Test handling of DST transition dates."""
        # This test would be more meaningful with a specific timezone library
        # For now, test with UTC (no DST) and document the limitation

        # Spring forward date (would be 2 AM -> 3 AM in DST zones)
        spring_forward = datetime.datetime(2024, 3, 10, 2, 30, 0, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": spring_forward})
        assert result == spring_forward

        # Fall back date (would be 2 AM -> 1 AM in DST zones)
        fall_back = datetime.datetime(2024, 11, 3, 1, 30, 0, tzinfo=datetime.timezone.utc)
        result = cel.evaluate("dt", {"dt": fall_back})
        assert result == fall_back

    @pytest.mark.parametrize(
        "invalid_datetime",
        [
            # Note: These would need to be objects that could potentially cause issues
            # but are hard to construct since Python's datetime is quite robust
        ],
    )
    def test_invalid_datetime_handling(self, invalid_datetime):
        """Test handling of potentially problematic datetime values."""
        # This test would be expanded if we identify specific problematic datetime patterns
        pass
