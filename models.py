"""
models.py - Core domain classes for the Clinic Appointment System.

Includes:
- Person (abstract base class)
- Patient (subclass of Person)
- Staff (abstract subclass of Person)
- Doctor, Nurse, Pharmacist (subclasses of Staff)
- Lecturer, MedicalLecturer (demonstrating multiple inheritance)
- Appointment (entity with lifecycle rules and invariants)

Student Details:
- Student ID (P): 2420420
- P mod 5 = 0  => Doctor fee = 40 + 5 * 0 = 40
- P mod 3 = 2  => Nurse fee = 10 + 2 = 12
- Pharmacist fee = 5
- P mod 4 = 0  => Twist 0 (Waiting list)
"""

from abc import ABC, abstractmethod


# =====================================================================
# Student Configuration Constants
# =====================================================================
STUDENT_ID = 2420420
DOCTOR_BASE_FEE = 40 + 5 * (STUDENT_ID % 5)   # 40 + 5 * 0 = 40
NURSE_BASE_FEE = 10 + (STUDENT_ID % 3)        # 10 + 2 = 12
PHARMACIST_FEE = 5


# =====================================================================
# Person Hierarchy
# =====================================================================
class Person(ABC):
    """
    Abstract base class representing a human in the clinic system.
    Demonstrates encapsulation: fields _id and _name are protected and private.
    """

    # Class-level counter to track constructor execution for diamond problem demonstration (Part 5)
    constructor_count = 0

    def __init__(self, person_id: int, name: str, **kwargs):
        """
        Initialize Person with id and name.
        Validates that id is a positive integer and name is non-empty.
        Uses **kwargs to enable cooperative multiple inheritance via super().
        """
        # Validate person_id: must be an int and > 0
        if not isinstance(person_id, int) or isinstance(person_id, bool) or person_id <= 0:
            raise ValueError(f"Person ID must be a positive integer, got: {person_id!r}")

        # Validate name: must be a non-empty string after stripping whitespace
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Person name cannot be empty or whitespace, got: {name!r}")

        # Increment counter to prove how many times Person.__init__ is executed
        Person.constructor_count += 1

        self._id = person_id
        self._name = name.strip()

        # Cooperative call to the next class in the Method Resolution Order (MRO)
        super().__init__(**kwargs)

    @property
    def id(self) -> int:
        """Read-only access to person id."""
        return self._id

    @property
    def name(self) -> str:
        """Read-only access to person name."""
        return self._name

    @abstractmethod
    def role(self) -> str:
        """Abstract method: each subclass must provide its role description."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._id}, name='{self._name}')"


class Patient(Person):
    """
    A patient visiting the clinic.
    """

    def __init__(self, patient_id: int, name: str, **kwargs):
        super().__init__(person_id=patient_id, name=name, **kwargs)

    def role(self) -> str:
        return "Patient"


class Staff(Person):
    """
    Abstract class for clinic medical staff.
    Adds the abstract method fee() for appointment charging.
    """

    def __init__(self, staff_id: int, name: str, **kwargs):
        super().__init__(person_id=staff_id, name=name, **kwargs)

    @abstractmethod
    def fee(self) -> int:
        """Abstract method: returns consultation fee per hour."""
        pass


class Doctor(Staff):
    """
    Medical doctor. Consultation fee formula: 40 + 5 * (P mod 5).
    For P = 2420420, 2420420 % 5 = 0, so fee = 40.
    """

    def __init__(self, staff_id: int, name: str, **kwargs):
        super().__init__(staff_id=staff_id, name=name, **kwargs)

    def role(self) -> str:
        return "Doctor"

    def fee(self) -> int:
        return DOCTOR_BASE_FEE


class Nurse(Staff):
    """
    Nurse practitioner. Consultation fee formula: 10 + (P mod 3).
    For P = 2420420, 2420420 % 3 = 2, so fee = 12.
    """

    def __init__(self, staff_id: int, name: str, **kwargs):
        super().__init__(staff_id=staff_id, name=name, **kwargs)

    def role(self) -> str:
        return "Nurse"

    def fee(self) -> int:
        return NURSE_BASE_FEE


class Pharmacist(Staff):
    """
    Pharmacist. Fixed fee: 5.
    Added cleanly via polymorphism without modifying existing loops or Clinic logic.
    """

    def __init__(self, staff_id: int, name: str, **kwargs):
        super().__init__(staff_id=staff_id, name=name, **kwargs)

    def role(self) -> str:
        return "Pharmacist"

    def fee(self) -> int:
        return PHARMACIST_FEE


# =====================================================================
# Academic & Multiple Inheritance (Part 5)
# =====================================================================
class Lecturer(Person):
    """
    Academic lecturer teaching at university.
    Demonstrates inheritance branch for the diamond problem.
    """

    def __init__(self, person_id: int, name: str, module_name: str, **kwargs):
        if not isinstance(module_name, str) or not module_name.strip():
            raise ValueError("Module name cannot be empty.")
        self._module_name = module_name.strip()
        super().__init__(person_id=person_id, name=name, **kwargs)

    @property
    def module_name(self) -> str:
        return self._module_name

    def role(self) -> str:
        return "Lecturer"


class MedicalLecturer(Doctor, Lecturer):
    """
    Medical Lecturer: combines Doctor (clinical duties) and Lecturer (teaching duties).
    Solves the diamond problem using Python's C3 MRO and super().__init__().

    MRO: MedicalLecturer -> Doctor -> Staff -> Lecturer -> Person -> object.
    Person.__init__() runs exactly ONCE.
    """

    def __init__(self, person_id: int, name: str, module_name: str):
        # Pass arguments cooperatively to super()
        super().__init__(
            staff_id=person_id,
            name=name,
            module_name=module_name,
        )

    def role(self) -> str:
        # Assignment Part 5 requirement: role() returning "Doctor and Lecturer"
        return "Doctor and Lecturer"

    def fee(self) -> int:
        """
        Consultation fee for clinical appointment.
        Returns Doctor's fee (40) because in the clinic, an appointment is a medical
        consultation. Teaching is funded separately by academic salary.
        """
        return Doctor.fee(self)


# =====================================================================
# Appointment Class
# =====================================================================
# INVARIANTS of Appointment:
# 1. id is a strictly positive integer (> 0) and is immutable once created.
# 2. patient is a valid Patient instance and cannot be null/None.
# 3. staff is a valid Staff instance and cannot be null/None.
# 4. start_hour is an integer between 0 and 168 inclusive (valid week simulation).
# 5. duration is always exactly 1 hour (end_hour = start_hour + 1).
# 6. status is strictly one of {"PENDING", "CONFIRMED", "CANCELLED"}.
# 7. Lifecycle transitions are strictly unidirectional:
#       PENDING -> CONFIRMED
#       PENDING -> CANCELLED
#       CONFIRMED -> CANCELLED
# 8. Once status is CANCELLED, it can NEVER return to any other status (terminal state).
# 9. An appointment can NEVER be cancelled once it has started (current_hour >= start_hour).
# 10. A CONFIRMED appointment cannot be cancelled less than 2 hours before start (start_hour - current_hour < 2).
class Appointment:
    """
    Represents a 1-hour clinic appointment between a Patient and a Staff member.
    """

    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_CANCELLED = "CANCELLED"

    VALID_STATUSES = {STATUS_PENDING, STATUS_CONFIRMED, STATUS_CANCELLED}

    def __init__(self, appt_id: int, patient: Patient, staff: Staff, start_hour: int):
        """
        Create a new appointment in PENDING status.
        """
        # 1. Validate ID
        if not isinstance(appt_id, int) or isinstance(appt_id, bool) or appt_id <= 0:
            raise ValueError(f"Appointment ID must be a positive integer, got: {appt_id!r}")

        # 2. Validate Patient
        if not isinstance(patient, Patient):
            raise TypeError("Appointment requires a valid Patient instance.")

        # 3. Validate Staff
        if not isinstance(staff, Staff):
            raise TypeError("Appointment requires a valid Staff instance.")

        # 4. Validate Start Hour (0 to 167 since appointment lasts 1 hour and ends by 168)
        if not isinstance(start_hour, int) or start_hour < 0 or start_hour >= 168:
            raise ValueError(f"Start hour must be an integer between 0 and 167, got: {start_hour}")

        self._id = appt_id
        self._patient = patient
        self._staff = staff
        self._start_hour = start_hour
        self._status = self.STATUS_PENDING

    # Read-only property getters
    @property
    def id(self) -> int:
        return self._id

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
    def status(self) -> str:
        return self._status

    def confirm(self) -> None:
        """
        Transition status from PENDING to CONFIRMED.
        Raises ValueError if appointment is not in PENDING status.
        """
        if self._status == self.STATUS_CANCELLED:
            raise ValueError(f"Cannot confirm appointment #{self._id}: it has already been CANCELLED.")
        if self._status == self.STATUS_CONFIRMED:
            raise ValueError(f"Appointment #{self._id} is already CONFIRMED.")
        self._status = self.STATUS_CONFIRMED

    def cancel(self, current_hour: int) -> None:
        """
        Transition status to CANCELLED enforcing the three assignment cancellation rules:
        1. A cancelled appointment can never return.
        2. No appointment can be cancelled once it has started (current_hour >= start_hour).
        3. A confirmed appointment cannot be cancelled less than 2 hours before start (start_hour - current_hour < 2).
        """
        # Rule 1: A cancelled appointment can never return or be cancelled again
        if self._status == self.STATUS_CANCELLED:
            raise ValueError(f"Cannot cancel appointment #{self._id}: it is already CANCELLED.")

        # Rule 2: Cannot be cancelled once it has started or finished
        if current_hour >= self._start_hour:
            raise ValueError(
                f"Cannot cancel appointment #{self._id}: already started or finished "
                f"(current hour: {current_hour}, start hour: {self._start_hour})."
            )

        # Rule 3: Confirmed appointment cannot be cancelled less than 2 hours before start
        if self._status == self.STATUS_CONFIRMED:
            hours_until_start = self._start_hour - current_hour
            if hours_until_start < 2:
                raise ValueError(
                    f"Cannot cancel confirmed appointment #{self._id}: less than 2 hours before start "
                    f"({hours_until_start} hour(s) left, minimum 2 required)."
                )

        # Transition to CANCELLED
        self._status = self.STATUS_CANCELLED

    def __repr__(self) -> str:
        return (
            f"Appointment(id={self._id}, patient={self._patient.name}, "
            f"staff={self._staff.name}, hour={self._start_hour}, status={self._status})"
        )
