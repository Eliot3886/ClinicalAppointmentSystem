"""
clock.py - Time simulation for the Clinic Appointment System.

Constraint from specification:
Time is a whole number of hours from 0 to 168 (one week, 7 days * 24 hours).
Every appointment lasts exactly 1 hour and has a start hour.
Your code must never read the computer clock; it must ask a Clock object for now().
"""


class Clock:
    """
    Simulated clock that tracks time in whole hours from 0 to 168.
    Hour 0 is Monday 00:00, and Hour 168 is Sunday 24:00 (end of week).
    """

    MIN_HOUR = 0
    MAX_HOUR = 168

    def __init__(self, start_hour: int = 0):
        """
        Initialize the clock at a given hour (default is 0).
        Rejects invalid hours outside [0, 168].
        """
        if not isinstance(start_hour, int):
            raise TypeError("Clock hour must be an integer.")
        if start_hour < self.MIN_HOUR or start_hour > self.MAX_HOUR:
            raise ValueError(f"Hour must be between {self.MIN_HOUR} and {self.MAX_HOUR}.")
        self._current_hour = start_hour

    def now(self) -> int:
        """Return the current simulated hour."""
        return self._current_hour

    def advance(self, hours: int = 1) -> int:
        """
        Advance the clock by a positive number of hours.
        Returns the new current hour.
        """
        if not isinstance(hours, int) or hours <= 0:
            raise ValueError("Advance hours must be a positive integer.")
        if self._current_hour + hours > self.MAX_HOUR:
            raise ValueError(f"Cannot advance past end of week ({self.MAX_HOUR} hours).")
        self._current_hour += hours
        return self._current_hour

    def set_time(self, hour: int) -> int:
        """
        Set the clock directly to a specific hour (e.g., for testing).
        """
        if not isinstance(hour, int):
            raise TypeError("Clock hour must be an integer.")
        if hour < self.MIN_HOUR or hour > self.MAX_HOUR:
            raise ValueError(f"Hour must be between {self.MIN_HOUR} and {self.MAX_HOUR}.")
        self._current_hour = hour
        return self._current_hour

    def __repr__(self) -> str:
        return f"Clock(hour={self._current_hour}/{self.MAX_HOUR})"
