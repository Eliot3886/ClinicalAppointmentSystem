"""Clinic Appointment System (Python).

Time is a whole number of hours from 0 to 168 (one week). Every appointment
lasts exactly one hour. Nothing in this file reads the computer clock: every
"what time is it?" question is answered by a Clock object's now().
"""
from __future__ import annotations

import inspect
import operator
import sys
from abc import ABC, abstractmethod
from enum import Enum
from functools import wraps

# Working P value (see README). The fees and the twist (P mod 4 = 0 -> waiting list)
# depend on it.
P = 2420420

WEEK_HOURS = 168


# ---------------------------------------------------------------------------
# Validation helpers (no isinstance / type checks anywhere in this file)
# ---------------------------------------------------------------------------

def require_whole_number(value, label: str) -> int:
    """Return value as an int or raise ValueError.

    operator.index() only accepts real whole numbers, so 2.5, "3" and None are
    rejected without any isinstance/type check. True/False are rejected too,
    because Python treats them as 1/0.
    """
    if value is True or value is False:
        raise ValueError(f"{label} must be a whole number, not {value}.")
    try:
        return operator.index(value)
    except TypeError:
        raise ValueError(f"{label} must be a whole number (got {value!r}).") from None


def require_positive_id(value, label: str = "ID") -> int:
    number = require_whole_number(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be positive (got {number}).")
    return number


def require_name(value, label: str = "Name") -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{label} cannot be empty.")
    return text


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------

class Clock(ABC):
    """The only source of 'now' in the system."""

    @abstractmethod
    def now(self) -> int:
        raise NotImplementedError


class ManualClock(Clock):
    """A clock that only moves when told to, so demos and tests are repeatable."""

    def __init__(self, start_hour: int = 0) -> None:
        self._hour = 0
        self.set(start_hour)

    def now(self) -> int:
        return self._hour

    def set(self, hour: int) -> None:
        hour = require_whole_number(hour, "Hour")
        if not 0 <= hour <= WEEK_HOURS:
            raise ValueError(f"Hour must be from 0 to {WEEK_HOURS} (got {hour}).")
        self._hour = hour

    def advance(self, hours: int = 1) -> None:
        hours = require_whole_number(hours, "Hours")
        if hours < 0:
            raise ValueError("The clock cannot go backwards.")
        self.set(self._hour + hours)


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class Person(ABC):
    # Counts how many times Person.__init__ has run. Used to show that a
    # MedicalLecturer contains exactly one Person.
    constructor_calls = 0

    def __init__(self, name: str, person_id: int) -> None:
        self._name = require_name(name)
        self._id = require_positive_id(person_id)
        Person.constructor_calls += 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def person_id(self) -> int:
        return self._id

    @abstractmethod
    def role(self) -> str:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.role()} {self._name} (id {self._id})"


class Patient(Person):
    def role(self) -> str:
        return "Patient"


class Staff(Person):
    """Every kind of staff member answers role() and fee() for itself, so the
    Clinic and the printing loop never need to know which kind it is."""

    @abstractmethod
    def fee(self) -> int:
        raise NotImplementedError


class Doctor(Staff):
    def role(self) -> str:
        return "Doctor"

    def fee(self) -> int:
        return 40 + 5 * (P % 5)


class Nurse(Staff):
    def role(self) -> str:
        return "Nurse"

    def fee(self) -> int:
        return 10 + (P % 3)


class Pharmacist(Staff):
    def role(self) -> str:
        return "Pharmacist"

    def fee(self) -> int:
        return 5


class Lecturer(Person):
    def __init__(self, name: str, person_id: int, module_name: str) -> None:
        self._module_name = require_name(module_name, "Module name")
        # Cooperative super(): in a MedicalLecturer this reaches Person exactly once.
        super().__init__(name, person_id)

    @property
    def module_name(self) -> str:
        return self._module_name

    def role(self) -> str:
        return "Lecturer"


class MedicalLecturer(Doctor, Lecturer):
    """Both a Doctor and a Lecturer, built on exactly one Person.

    Method resolution order (MRO):
        MedicalLecturer -> Doctor -> Staff -> Lecturer -> Person
    Person appears once, and every __init__ calls super(), so Person.__init__
    runs exactly once.
    """

    def __init__(self, name: str, person_id: int, module_name: str) -> None:
        super().__init__(name, person_id, module_name)

    def role(self) -> str:
        return "Doctor and Lecturer"

    def fee(self) -> int:
        # The clinic only charges for clinical work. Lecturing is not a clinic
        # service, so a MedicalLecturer charges the normal Doctor fee.
        return super().fee()


# ---------------------------------------------------------------------------
# Appointment
# ---------------------------------------------------------------------------

class AppointmentStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


# Appointment invariants (true after __init__ and after every method call):
# - appointment_id is a positive whole number and never changes.
# - patient and staff are set when the appointment is created and never change.
# - start_hour is a whole number from 0 to 167. The appointment lasts exactly
#   1 hour, so end_hour = start_hour + 1 <= 168.
# - status is always PENDING, CONFIRMED or CANCELLED and only moves along
#   PENDING -> CONFIRMED, PENDING -> CANCELLED or CONFIRMED -> CANCELLED.
# - Once CANCELLED, the status never changes again.
# - A CONFIRMED appointment is never cancelled less than 2 hours before it starts.
# - No appointment is cancelled or confirmed once it has started (now >= start_hour).
# - cancel_reason is empty unless the status is CANCELLED.
class Appointment:
    DURATION_HOURS = 1
    MIN_NOTICE_TO_CANCEL_CONFIRMED = 2

    _LEGAL_MOVES = {
        AppointmentStatus.PENDING: frozenset(
            {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED}
        ),
        AppointmentStatus.CONFIRMED: frozenset({AppointmentStatus.CANCELLED}),
        AppointmentStatus.CANCELLED: frozenset(),
    }

    def __init__(
        self,
        appointment_id: int,
        patient: Patient,
        staff: Staff,
        start_hour: int,
    ) -> None:
        if patient is None or staff is None:
            raise ValueError("An appointment needs a patient and a staff member.")
        start_hour = require_whole_number(start_hour, "Start hour")
        if not 0 <= start_hour <= WEEK_HOURS - self.DURATION_HOURS:
            raise ValueError(
                f"Start hour must be from 0 to {WEEK_HOURS - self.DURATION_HOURS} "
                f"(got {start_hour})."
            )

        self._appointment_id = require_positive_id(appointment_id, "Appointment ID")
        self._patient = patient
        self._staff = staff
        self._start_hour = start_hour
        self._status = AppointmentStatus.PENDING
        self._cancel_reason = ""

    # --- read-only view -----------------------------------------------------

    @property
    def appointment_id(self) -> int:
        return self._appointment_id

    @property
    def patient(self) -> Patient:
        return self._patient

    @property
    def staff(self) -> Staff:
        return self._staff

    @property
    def start_hour(self) -> int:
        return self._start_hour

    @property
    def end_hour(self) -> int:
        return self._start_hour + self.DURATION_HOURS

    @property
    def status(self) -> AppointmentStatus:
        return self._status

    @property
    def cancel_reason(self) -> str:
        return self._cancel_reason

    @property
    def is_active(self) -> bool:
        return self._status != AppointmentStatus.CANCELLED

    def why_cannot_cancel(self, now: int) -> str | None:
        """Return the reason this appointment cannot be cancelled at `now`, or None."""
        if self._status == AppointmentStatus.CANCELLED:
            return "already cancelled (a cancelled appointment can never come back)"
        if now >= self._start_hour:
            return f"already started (it started at hour {self._start_hour}, now is {now})"
        hours_left = self._start_hour - now
        if (
            self._status == AppointmentStatus.CONFIRMED
            and hours_left < self.MIN_NOTICE_TO_CANCEL_CONFIRMED
        ):
            return (
                f"too late (confirmed appointments need "
                f"{self.MIN_NOTICE_TO_CANCEL_CONFIRMED} hours' notice, "
                f"only {hours_left} left)"
            )
        return None

    # --- status changes --------------------------------------------------------
    # These start with "_" because only the Clinic may call them. Going through
    # the Clinic is what guarantees the change is logged and that a freed slot
    # is offered to the waiting list.

    def _confirm(self, now: int) -> None:
        if self.is_active and now >= self._start_hour:
            raise ValueError(f"already started (it started at hour {self._start_hour})")
        self._move_to(AppointmentStatus.CONFIRMED)

    def _cancel(self, now: int, reason: str = "cancelled by request") -> None:
        problem = self.why_cannot_cancel(now)
        if problem:
            raise ValueError(problem)
        self._move_to(AppointmentStatus.CANCELLED)
        self._cancel_reason = reason

    def _move_to(self, new_status: AppointmentStatus) -> None:
        if new_status not in self._LEGAL_MOVES[self._status]:
            message = f"cannot change {self._status.value} to {new_status.value}"
            if self._status == AppointmentStatus.CANCELLED:
                message += " (a cancelled appointment can never come back)"
            raise ValueError(message)
        self._status = new_status

    def __repr__(self) -> str:
        return (
            f"#{self._appointment_id} hour {self._start_hour}-{self.end_hour} "
            f"{self._patient.name} with {self._staff.name} [{self._status.value}]"
        )


# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------

class LogError(Exception):
    """Raised when the log itself cannot be written or closed."""


class AppointmentLog:
    """Appointment log used as a context manager:

        with AppointmentLog("appointments.log") as log:
            ...

    Python's `with` statement calls __enter__ once at the start and __exit__
    once at the end, even if an exception escapes the block. So the file is
    opened exactly once and closed exactly once.
    """

    def __init__(self, path: str, opener=open, echo: bool = True) -> None:
        self._path = path
        self._opener = opener  # can be replaced in tests to simulate failures
        self._echo = echo
        self._file = None
        self._used = False

    @property
    def is_open(self) -> bool:
        return self._file is not None

    def __enter__(self) -> "AppointmentLog":
        if self._used:
            raise LogError("This log was already opened once; create a new AppointmentLog.")
        self._used = True
        self._file = self._opener(self._path, "a", encoding="utf-8")
        print("[log] opened")
        return self

    def write(self, message: str) -> None:
        if self._file is None:
            raise LogError("The log is not open.")
        try:
            self._file.write(message + "\n")
            self._file.flush()
        except OSError as error:
            # An action we cannot record must not pass silently (see README, D5).
            raise LogError(f"could not write to the log: {error}") from error
        if self._echo:
            print(f"[log] {message}")

    def __exit__(self, error_type, error, traceback) -> bool:
        file_to_close, self._file = self._file, None
        try:
            if file_to_close is not None:
                file_to_close.close()
        except OSError as close_error:
            if error is None:
                raise LogError(f"could not close the log: {close_error}") from close_error
            # Something already went wrong. Report the close failure but do not
            # let it hide the original error, which is the more important one.
            print(f"[log] WARNING: could not close the log: {close_error}", file=sys.stderr)
        finally:
            print("[log] closed")
        return False  # never swallow the original exception


def logged_action(label_template: str):
    """Log '<label>: OK' when the method succeeds, or 'FAILED <label>: <reason>'
    when it raises. The error is re-raised so the caller still sees it.

    label_template uses the method's parameter names, e.g. "cancel #{appointment_id}".
    """

    def decorator(method):
        signature = inspect.signature(method)

        @wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                arguments = signature.bind(self, *args, **kwargs).arguments
                label = label_template.format(**arguments)
            except (TypeError, KeyError, AttributeError, IndexError):
                label = method.__name__

            try:
                result = method(self, *args, **kwargs)
            except Exception as error:
                self._log.write(f"FAILED {label}: {error}")
                raise

            self._log.write(f"{label}: OK")
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Clinic
# ---------------------------------------------------------------------------

# Clinic invariants (true after __init__ and after every public method call):
# - Every id (patients, staff and appointments together) is used at most once.
# - Every appointment's patient and staff member are registered with this clinic.
# - No patient and no staff member has two non-cancelled appointments that
#   start at the same hour.
# - New appointments are only booked for hours that have not started yet.
# - Each waiting list belongs to one registered staff member and holds
#   registered patients in the order they joined, with nobody listed twice.
# - Internal lists are never handed out. Callers only get tuples (read-only copies).
# - Every public action is written to the log, whether it succeeds or fails.
class Clinic:
    def __init__(self, clock: Clock, log) -> None:
        self._clock = clock
        self._log = log
        self._patients: list[Patient] = []
        self._staff: list[Staff] = []
        self._appointments: list[Appointment] = []
        self._used_ids: set[int] = set()
        self._waiting_lists: dict[int, list[Patient]] = {}

    # --- read-only views (copies, never the internal lists) ------------------

    @property
    def patients(self) -> tuple[Patient, ...]:
        return tuple(self._patients)

    @property
    def staff(self) -> tuple[Staff, ...]:
        return tuple(self._staff)

    @property
    def appointments(self) -> tuple[Appointment, ...]:
        return tuple(self._appointments)

    def waiting_list(self, staff_member: Staff) -> tuple[Patient, ...]:
        return tuple(self._waiting_lists.get(staff_member.person_id, []))

    def find_appointment(self, appointment_id: int) -> Appointment:
        for appointment in self._appointments:
            if appointment.appointment_id == appointment_id:
                return appointment
        raise ValueError(f"appointment #{appointment_id} was not found")

    # --- registration -------------------------------------------------------

    @logged_action("register patient {patient.name} (id {patient.person_id})")
    def register_patient(self, patient: Patient) -> None:
        self._claim_id(patient.person_id)
        self._patients.append(patient)

    @logged_action("register staff {staff_member.name} (id {staff_member.person_id})")
    def register_staff(self, staff_member: Staff) -> None:
        self._claim_id(staff_member.person_id)
        self._staff.append(staff_member)

    # --- booking --------------------------------------------------------------

    @logged_action("book #{appointment_id}")
    def book_appointment(
        self,
        appointment_id: int,
        patient: Patient,
        staff_member: Staff,
        start_hour: int,
    ) -> Appointment:
        self._require_registered(patient, staff_member)
        appointment_id = require_positive_id(appointment_id, "Appointment ID")
        if appointment_id in self._used_ids:
            raise ValueError(f"id {appointment_id} is already in use")

        now = self._clock.now()
        start_hour = require_whole_number(start_hour, "Start hour")
        if start_hour <= now:
            raise ValueError(f"hour {start_hour} has already started (now is {now})")

        clash = self._clash(patient, staff_member, start_hour)
        if clash:
            raise ValueError(clash)

        appointment = Appointment(appointment_id, patient, staff_member, start_hour)
        self._add(appointment)
        return appointment

    @logged_action("confirm #{appointment_id}")
    def confirm_appointment(self, appointment_id: int) -> Appointment:
        appointment = self.find_appointment(appointment_id)
        appointment._confirm(self._clock.now())
        return appointment

    def cancel_appointment(self, appointment_id: int) -> Appointment:
        appointment = self._cancel(appointment_id)
        # Only after the cancel has been logged, offer the freed slot (twist 0).
        self._offer_freed_slot(appointment)
        return appointment

    @logged_action("cancel #{appointment_id}")
    def _cancel(self, appointment_id: int) -> Appointment:
        appointment = self.find_appointment(appointment_id)
        appointment._cancel(self._clock.now())
        return appointment

    # --- twist (P mod 4 = 0): waiting list ------------------------------------

    @logged_action("join waiting list: {patient.name} for {staff_member.name}")
    def join_waiting_list(self, patient: Patient, staff_member: Staff) -> None:
        self._require_registered(patient, staff_member)
        queue = self._waiting_lists.setdefault(staff_member.person_id, [])
        if any(waiting.person_id == patient.person_id for waiting in queue):
            raise ValueError(f"{patient.name} is already on {staff_member.name}'s waiting list")
        queue.append(patient)

    def _offer_freed_slot(self, cancelled: Appointment) -> Appointment | None:
        staff_member = cancelled.staff
        hour = cancelled.start_hour
        queue = self._waiting_lists.get(staff_member.person_id, [])

        for patient in list(queue):
            if self._clash(patient, staff_member, hour) is not None:
                continue  # this patient is busy at that hour; try the next one
            offered = Appointment(self._next_free_id(), patient, staff_member, hour)
            self._add(offered)
            queue.remove(patient)
            self._log.write(
                f"OFFERED freed slot (hour {hour} with {staff_member.name}) "
                f"to {patient.name} as PENDING #{offered.appointment_id}"
            )
            return offered

        if queue:
            self._log.write(
                f"no one on {staff_member.name}'s waiting list is free at hour {hour}"
            )
        return None

    # --- helpers -------------------------------------------------------------------

    def _claim_id(self, object_id: int) -> None:
        if object_id in self._used_ids:
            raise ValueError(f"id {object_id} is already in use")
        self._used_ids.add(object_id)

    def _add(self, appointment: Appointment) -> None:
        self._claim_id(appointment.appointment_id)
        self._appointments.append(appointment)

    def _next_free_id(self) -> int:
        return max(self._used_ids, default=0) + 1

    def _require_registered(self, patient: Patient, staff_member: Staff) -> None:
        if patient not in self._patients:
            raise ValueError(f"{patient!r} is not a registered patient")
        if staff_member not in self._staff:
            raise ValueError(f"{staff_member!r} is not a registered staff member")

    def _clash(self, patient: Patient, staff_member: Staff, hour: int) -> str | None:
        """Return why this booking would double-book someone, or None if it is fine."""
        for existing in self._appointments:
            if not existing.is_active or existing.start_hour != hour:
                continue
            if existing.patient.person_id == patient.person_id:
                return (
                    f"{patient.name} already has appointment "
                    f"#{existing.appointment_id} at hour {hour}"
                )
            if existing.staff.person_id == staff_member.person_id:
                return (
                    f"{staff_member.name} already has appointment "
                    f"#{existing.appointment_id} at hour {hour}"
                )
        return None


# ---------------------------------------------------------------------------
# Demo (Part 8)
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n=== {title} ===")


def expect_failure(description: str, action) -> None:
    """Run an action that should fail, and show why it failed."""
    try:
        action()
    except ValueError as error:
        print(f"  expected failure ({description}): {error}")
    else:
        print(f"  !! {description} unexpectedly succeeded")


def run_demo(log_path: str = "appointments.log") -> None:
    with AppointmentLog(log_path) as log:
        clock = ManualClock(10)
        clinic = Clinic(clock, log)
        print(f"Clock starts at hour {clock.now()}")

        section("1. Constructors reject bad data")
        expect_failure("empty name", lambda: Patient("   ", 10))
        expect_failure("zero id", lambda: Patient("Zoe", 0))
        expect_failure("negative id", lambda: Nurse("Nurse Zoe", -4))
        expect_failure("id that is not a whole number", lambda: Doctor("Dr. Zoe", 2.5))

        section("2. MedicalLecturer builds exactly one Person")
        before = Person.constructor_calls
        medical_lecturer = MedicalLecturer("Dr. Tariro", 50, "Public Health")
        print(f"  Person constructor ran {Person.constructor_calls - before} time(s)")
        print(f"  role(): {medical_lecturer.role()}")
        print(f"  module: {medical_lecturer.module_name}")
        print(f"  MRO: {' -> '.join(c.__name__ for c in MedicalLecturer.__mro__[:5])}")

        section("3. Register everyone (ids must be unique)")
        ava = Patient("Ava", 1)
        ben = Patient("Ben", 2)
        chipo = Patient("Chipo", 8)
        doctor = Doctor("Dr. Ncube", 3)
        nurse = Nurse("Nurse Moyo", 6)
        pharmacist = Pharmacist("Pharmacist Dube", 7)
        for patient in (ava, ben, chipo):
            clinic.register_patient(patient)
        for staff_member in (doctor, nurse, pharmacist, medical_lecturer):
            clinic.register_staff(staff_member)
        expect_failure("duplicate id", lambda: clinic.register_patient(Patient("Copycat", 3)))

        section("4. One loop prints every staff member's role and fee")
        for staff_member in clinic.staff:
            print(f"  {staff_member.role():<20} fee: {staff_member.fee()}")

        section("5. Booking rules")
        clinic.book_appointment(20, ava, doctor, 15)
        clinic.confirm_appointment(20)
        expect_failure("patient double-booked", lambda: clinic.book_appointment(21, ava, nurse, 15))
        expect_failure("staff double-booked", lambda: clinic.book_appointment(22, chipo, doctor, 15))
        expect_failure("id already used by a person", lambda: clinic.book_appointment(3, chipo, nurse, 16))
        expect_failure("hour already started", lambda: clinic.book_appointment(23, chipo, nurse, 9))
        expect_failure("hour outside the week", lambda: clinic.book_appointment(24, chipo, nurse, 168))

        section("6. Twist: waiting list (P mod 4 = 0)")
        clinic.join_waiting_list(ben, doctor)
        expect_failure("joining twice", lambda: clinic.join_waiting_list(ben, doctor))
        clinic.cancel_appointment(20)  # 5 hours' notice, so this is allowed
        offered = clinic.appointments[-1]
        print(f"  freed slot went to: {offered}")

        section("7. Status rules")
        expect_failure("cancelled appointment cannot come back", lambda: clinic.confirm_appointment(20))
        expect_failure("cancelled appointment cannot be cancelled again", lambda: clinic.cancel_appointment(20))
        clinic.book_appointment(30, chipo, nurse, 12)
        clinic.confirm_appointment(30)
        clinic.book_appointment(31, ava, pharmacist, 13)  # stays PENDING
        clock.advance(1)
        print(f"  clock moved to hour {clock.now()}")
        expect_failure("confirmed, only 1 hour before start", lambda: clinic.cancel_appointment(30))
        clock.set(13)
        print(f"  clock moved to hour {clock.now()}")
        expect_failure("appointment already started", lambda: clinic.cancel_appointment(31))

        section("8. Final appointments (read-only copy)")
        for appointment in clinic.appointments:
            print(f"  {appointment}")

        section("9. Deliberate crash in the middle of an operation")
        print("  Raising an unexpected error inside the `with` block...")
        raise RuntimeError("simulated power cut")


if __name__ == "__main__":
    try:
        run_demo()
    except RuntimeError as error:
        print(f"\nProgram caught: {error}")
        print("Notice '[log] closed' was printed above, before this line, even though the demo crashed.")
