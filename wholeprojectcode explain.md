# Complete Code Explanation Guide: Clinic Appointment System

This guide provides a comprehensive, section-by-section and line-by-line breakdown of the entire codebase (`main.py` and `test_clinic.py`). It is designed to give you complete mastery over every class, method, validation helper, and design decision so you can explain every detail with confidence during your oral demo and viva.

---

# Part 1: Architecture of `main.py`

## 1. Top-Level Imports & Global Setup (Lines 1 – 21)

```python
from __future__ import annotations
import inspect
import operator
import sys
from abc import ABC, abstractmethod
from enum import Enum
from functools import wraps
```
- **`from __future__ import annotations`**: Postpones type hint evaluation so classes can reference themselves or types defined later in the file without quotes (e.g. `def __enter__(self) -> AppointmentLog:`).
- **`operator`**: Used for `operator.index()`, a built-in Python function that converts real whole numbers (`int`) to integers without using `isinstance` or type tags.
- **`sys`**: Used to write warnings to `sys.stderr` when a secondary logging error occurs.
- **`abc` (`ABC`, `abstractmethod`)**: Implements Abstract Base Classes and enforces interface contracts.
- **`enum` (`Enum`)**: Implements the finite state machine states for `AppointmentStatus`.
- **`functools.wraps`**: Ensures decorators preserve the original function's name and docstring.
- **`P = 2420420`**: The student ID integer component. Determines the staff fee formulas and Twist 0 ($P \pmod 4 = 0$, Waiting List).
- **`WEEK_HOURS = 168`**: The maximum number of hours in a week ($7 \times 24 = 168$).

---

## 2. Validation Helpers: Zero Type Tags / No `isinstance` (Lines 27 – 53)

The assignment strictly mandates:
> *"How do you do this with no instanceof / isinstance / type tags anywhere..."*

```python
def require_whole_number(value, label: str) -> int:
    if value is True or value is False:
        raise ValueError(f"{label} must be a whole number, not {value}.")
    try:
        return operator.index(value)
    except TypeError:
        raise ValueError(f"{label} must be a whole number (got {value!r}).") from None
```
- **Why this is clever:** In Python, `bool` is a subclass of `int` (`isinstance(True, int) == True`). We first reject `True` and `False`.
- `operator.index(value)` calls the object's `__index__()` dunder method. It accepts Python integers, but automatically rejects floats (`2.5`), strings (`"3"`), and `None` with a `TypeError`. We catch this and convert it to a user-friendly `ValueError`.
- This ensures rigorous integer validation with **zero `isinstance` or `type(value) == int` checks**!

```python
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
```
- Validates that IDs are strictly $> 0$ ($1, 2, 3, \dots$).
- Validates names by stripping leading/trailing whitespace; rejects empty strings or whitespace-only inputs.

---

## 3. Clock Abstraction (Lines 60 – 89)

```python
class Clock(ABC):
    @abstractmethod
    def now(self) -> int:
        raise NotImplementedError

class ManualClock(Clock):
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
```
- **Fulfills the prompt constraint:** *"Your code must never read the computer clock; it must ask a Clock object for `now()`."*
- Decouples the business logic from real-world wall-clock time.
- `ManualClock` allows unit tests and the live demo to fast-forward time deterministically without waiting real hours.

---

## 4. Person Hierarchy & Multiple Inheritance (Lines 95 – 193)

```python
class Person(ABC):
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
```
- `Person` is abstract.
- `constructor_calls` is a **class-level counter** shared across all instances. Every time `Person.__init__` executes, it increments by 1.
- `_name` and `_id` are private encapsulated fields with read-only properties.

```python
class Patient(Person):
    def role(self) -> str:
        return "Patient"

class Staff(Person):
    @abstractmethod
    def fee(self) -> int:
        raise NotImplementedError
```
- `Staff` extends `Person` with an abstract `fee()` method.

```python
class Doctor(Staff):
    def role(self) -> str:
        return "Doctor"
    def fee(self) -> int:
        return 40 + 5 * (P % 5)  # 40 + 5 * 0 = 40

class Nurse(Staff):
    def role(self) -> str:
        return "Nurse"
    def fee(self) -> int:
        return 10 + (P % 3)      # 10 + 2 = 12

class Pharmacist(Staff):
    def role(self) -> str:
        return "Pharmacist"
    def fee(self) -> int:
        return 5
```
- Polymorphic fee calculations based on student $P = 2420420$.

```python
class Lecturer(Person):
    def __init__(self, name: str, person_id: int, module_name: str) -> None:
        self._module_name = require_name(module_name, "Module name")
        super().__init__(name, person_id)

    @property
    def module_name(self) -> str:
        return self._module_name

    def role(self) -> str:
        return "Lecturer"

class MedicalLecturer(Doctor, Lecturer):
    def __init__(self, name: str, person_id: int, module_name: str) -> None:
        super().__init__(name, person_id, module_name)

    def role(self) -> str:
        return "Doctor and Lecturer"

    def fee(self) -> int:
        return super().fee()
```
- **Diamond Inheritance & C3 Linearization:**
  - `MedicalLecturer` inherits from `Doctor` and `Lecturer`. Both inherit from `Person`.
  - Python establishes the Method Resolution Order (MRO):
    `MedicalLecturer` $\rightarrow$ `Doctor` $\rightarrow$ `Staff` $\rightarrow$ `Lecturer` $\rightarrow$ `Person` $\rightarrow$ `object`.
  - Because each class calls `super().__init__`, Python visits each class in the linearization order exactly once.
  - Therefore, `Person.__init__` runs **only once**, and `Person.constructor_calls` increments by exactly $1$.
  - `fee()` returns `Doctor.fee()` ($40$) because consultations are medical services, not university lectures.

---

## 5. Appointment & Finite State Machine (Lines 198 – 332)

```python
class AppointmentStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
```

```python
# Appointment Invariants:
# - appointment_id is a positive whole number and never changes.
# - patient and staff are set at creation and never change.
# - start_hour in [0, 167], duration = 1 hour, end_hour = start_hour + 1 <= 168.
# - status moves strictly: PENDING -> CONFIRMED, PENDING -> CANCELLED, CONFIRMED -> CANCELLED.
# - Once CANCELLED, status never changes again (terminal state).
# - A CONFIRMED appointment cannot be cancelled with < 2 hours notice.
# - No appointment can be cancelled or confirmed once now >= start_hour.
```

```python
class Appointment:
    DURATION_HOURS = 1
    MIN_NOTICE_TO_CANCEL_CONFIRMED = 2

    _LEGAL_MOVES = {
        AppointmentStatus.PENDING: frozenset({AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED}),
        AppointmentStatus.CONFIRMED: frozenset({AppointmentStatus.CANCELLED}),
        AppointmentStatus.CANCELLED: frozenset(),
    }
```
- **Formal State Transition Matrix:** Encoded in `_LEGAL_MOVES`. If a transition is not in the set (e.g. `CANCELLED` $\rightarrow$ `CONFIRMED`), it is rejected immediately.

```python
    def why_cannot_cancel(self, now: int) -> str | None:
        if self._status == AppointmentStatus.CANCELLED:
            return "already cancelled (a cancelled appointment can never come back)"
        if now >= self._start_hour:
            return f"already started (it started at hour {self._start_hour}, now is {now})"
        hours_left = self._start_hour - now
        if self._status == AppointmentStatus.CONFIRMED and hours_left < self.MIN_NOTICE_TO_CANCEL_CONFIRMED:
            return (
                f"too late (confirmed appointments need "
                f"{self.MIN_NOTICE_TO_CANCEL_CONFIRMED} hours' notice, only {hours_left} left)"
            )
        return None
```
- Centralizes all cancellation rules within `Appointment` (Information Expert principle).

```python
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
```
- `_confirm` and `_cancel` start with an underscore because **only `Clinic` is authorized to call them**. External code cannot bypass clinic logging or waiting list reallocation!

---

## 6. AppointmentLog & Action Decorator (Lines 342 – 434)

```python
class AppointmentLog:
    def __init__(self, path: str, opener=open, echo: bool = True) -> None:
        self._path = path
        self._opener = opener
        self._echo = echo
        self._file = None
        self._used = False
```
- Manages log file lifecycle. Accepts an optional `opener` parameter so unit tests can inject mock file openers to test disk failures.

```python
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
        self._file.write(message + "\n")
        self._file.flush()
        if self._echo:
            print(f"[log] {message}")

    def __exit__(self, error_type, error, traceback) -> bool:
        file_to_close, self._file = self._file, None
        try:
            if file_to_close is not None:
                file_to_close.close()
        finally:
            print("[log] closed")
        return False
```
- **Context Manager Guarantee:**
  - `__enter__` prints `[log] opened`.
  - `__exit__` guarantees `[log] closed` is printed and the file handle is flushed and closed, even if an exception occurs mid-operation (`try...finally`).
  - Returns `False` so exceptions are never silently swallowed.

```python
def logged_action(label_template: str):
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            ...
            try:
                result = method(self, *args, **kwargs)
            except Exception as error:
                self._log.write(f"FAILED {action_label}: {error}")
                raise
            self._log.write(f"{action_label}: OK")
            return result
        return wrapper
    return decorator
```
- Wraps clinic actions to automatically write `{action_label}: OK` on success, or `FAILED {action_label}: {error}` on failure before re-raising.

---

## 7. The `Clinic` Aggregate Root (Lines 436 – 588)

```python
class Clinic:
    def __init__(self, clock: Clock, log: AppointmentLog) -> None:
        self._clock = clock
        self._log = log
        self._patients: list[Patient] = []
        self._staff: list[Staff] = []
        self._appointments: list[Appointment] = []
        self._used_ids: set[int] = set()
        self._waiting_lists: dict[int, list[Patient]] = {}
```
- **Invariants of Clinic:**
  - `_used_ids`: Global set enforcing unique IDs across patients, staff, and appointments.
  - `_waiting_lists`: FIFO queue of waiting patients mapped by staff member ID.

```python
    @property
    def patients(self) -> tuple[Patient, ...]:
        return tuple(self._patients)

    @property
    def staff(self) -> tuple[Staff, ...]:
        return tuple(self._staff)

    @property
    def appointments(self) -> tuple[Appointment, ...]:
        return tuple(self._appointments)
```
- **Encapsulation / Immutability:** Always returns a read-only `tuple` copy. External code cannot call `.append()` or `.pop()` on the clinic's internal lists.

```python
    @logged_action("book #{appointment_id}")
    def book_appointment(self, appointment_id: int, patient: Patient, staff: Staff, start_hour: int) -> Appointment:
        ...
        for existing in self._appointments:
            if existing.is_active and existing.start_hour == start_hour:
                if existing.patient.person_id == patient.person_id:
                    raise ValueError(f"{patient.name} already has appointment #{existing.appointment_id} at hour {start_hour}")
                if existing.staff.person_id == staff.person_id:
                    raise ValueError(f"{staff.name} already has appointment #{existing.appointment_id} at hour {start_hour}")
```
- **Question 6 Rule:** Prohibits double booking for both patient and staff member at the same hour.

```python
    def _offer_slot_to_waiting_patient(self, cancelled: Appointment) -> Appointment | None:
        queue = self._waiting_lists.get(cancelled.staff.person_id, [])
        for candidate in list(queue):
            if not self._patient_is_free(candidate, cancelled.start_hour):
                continue
            queue.remove(candidate)
            new_id = self._next_available_id()
            appointment = Appointment(new_id, candidate, cancelled.staff, cancelled.start_hour)
            self._appointments.append(appointment)
            self._used_ids.add(new_id)
            self._log.write(f"OFFERED freed slot (hour {cancelled.start_hour} with {cancelled.staff.name}) to {candidate.name} as PENDING #{new_id}")
            return appointment
```
- **Twist 0 Automation:** Automatically iterates the waiting queue upon appointment cancellation. Offers the slot to the first candidate with no hour conflict, generates a fresh unique ID, creates a new `PENDING` appointment, and logs the offer.

---

## 8. Demo Walkthrough (`main.py` lines 595 – 706)

The demonstration in `main.py` covers 9 distinct sections:
1. **Bad Constructor Data:** Proves rejection of empty names, zero IDs, negative IDs, and floats.
2. **MedicalLecturer Single Initialization:** Verifies `Person.constructor_calls == 1`, prints MRO.
3. **Registration & ID Uniqueness:** Registers participants and catches duplicate ID attempts.
4. **Polymorphic Staff Fee Loop:** Prints role and fee with zero `isinstance` checks.
5. **Booking Rules:** Tests valid booking, double-booking prevention, booking in the past, and hour bounds ($0–167$).
6. **Twist 0 Waiting List:** Demonstrates queueing, double-queueing rejection, slot freeing, and automatic reallocation as `PENDING`.
7. **Status Rules & Cancellation Notice:** Demonstrates rejection of cancelled un-cancellation, rejection of cancellation $< 2$ hours before start (`FAILED cancel #30: too late ...`), and rejection after appointment start.
8. **Final Appointments View:** Shows final read-only tuple states.
9. **Deliberate Mid-Operation Crash:** Proves that `[log] closed` is still guaranteed to execute during an unhandled exception.

---

# Part 2: Architecture of `test_clinic.py` (36 Unit Tests)

`test_clinic.py` is divided into 8 test suites:

1. **`ConstructorTests`**: Tests rejection of empty names, whitespace names, non-positive IDs, booleans as IDs, floats as IDs, and empty module names.
2. **`MedicalLecturerTests`**: Tests that `Person.constructor_calls` increments by exactly 1, role is `"Doctor and Lecturer"`, and fee equals the Doctor rate.
3. **`FeeAndPolymorphismTests`**: Validates fee calculations against $P = 2420420$, proves a new subclass (`Physiotherapist`) can be added with zero changes, and uses the `ast` module to scan the entire source code to verify **zero `isinstance` / `issubclass` / `type()` checks exist**!
4. **`EncapsulationTests`**: Proves external mutation of `clinic.patients`, `clinic.staff`, and `clinic.appointments` fails (tuples), and that direct attribute assignment to `appointment.status` raises `AttributeError`.
5. **`BookingRuleTests`**: Tests staff collision, patient collision, clinic-wide ID uniqueness, hour boundaries, and unregistered participant rejection.
6. **`StatusTransitionTests`**: Tests the entire finite state machine table: `PENDING` $\rightarrow$ `CONFIRMED`, `PENDING` $\rightarrow$ `CANCELLED`, `CONFIRMED` $\rightarrow$ `CANCELLED` (at exactly 2 hours notice), rejection of cancellation at 1 hour notice, rejection of cancellation after start, and permanence of `CANCELLED`.
7. **`WaitingListTests`**: Tests FIFO queue allocation, skipping busy waiting patients, and logging order.
8. **`AppointmentLogTests`**: Tests single open/close lifecycle, write errors, close errors, and prevention of reopening.
