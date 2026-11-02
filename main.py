from abc import ABC, abstractmethod
from enum import Enum
from functools import wraps

P = 2420420


class Person(ABC):
    constructor_calls = 0
    def __init__(self, name: str, person_id: int) -> None:
        clean_name = name.strip()

        if not clean_name:
            raise ValueError("Name cannot be empty.")

        if isinstance(person_id, bool) or not isinstance(person_id, int) or person_id <= 0:
            raise ValueError("ID must be a positive number.")

        self._name = clean_name
        self._id = person_id
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


class Patient(Person):
    def role(self) -> str:
        return "Patient"


class Staff(Person):
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
        clean_module = module_name.strip()
        if not clean_module:
            raise ValueError("Module name cannot be empty.")

        self._module_name = clean_module
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

             
        
class AppointmentStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
class Clock(ABC):
    @abstractmethod
    def now(self) -> int:
        raise NotImplementedError

class ManualClock(Clock):
    def __init__(self, current_hour: int) -> None:
        self._current_hour = current_hour
    def now(self) -> int:
        return self._current_hour

# Appointment rules:
# - Its ID is a positive whole number.
# - Its patient and staff member are provided when it is created.
# - Its start hour is from 0 to 167.
# - Every appointment lasts exactly one hour.
# - It begins as PENDING.   


class Appointment:
    def __init__(
          self,
          appointment_id: int,
          patient: Patient,
          staff: Staff,
          start_hour: int,
          clock: Clock, 
    ) -> None:
        if appointment_id <= 0:
            raise ValueError("Appointment ID must be positive.")
        if isinstance(start_hour, bool) or not isinstance(start_hour, int):
            raise ValueError("Start hour must be a whole number.")
        if start_hour < 0 or start_hour >= 168:
            raise ValueError("Start hour must be from 0 to 167.")

        self._appointment_id = appointment_id
        self._patient = patient
        self._staff = staff
        self._start_hour = start_hour
        self._clock = clock
        self._status = AppointmentStatus.PENDING
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
    def status(self) -> AppointmentStatus:
        return self._status

    def confirm(self) -> None:
        if self._status != AppointmentStatus.PENDING:
            raise ValueError("Only a pending appointment can be confirmed.")

        self._status = AppointmentStatus.CONFIRMED

    def cancel(self) -> None:
        if self._status == AppointmentStatus.CANCELLED:
            raise ValueError("A cancelled appointment cannot be changed.")

        current_hour = self._clock.now()

        if current_hour >= self._start_hour:
            raise ValueError("Appointment has already started.")

        if (
            self._status == AppointmentStatus.CONFIRMED
            and self._start_hour - current_hour < 2
        ):
            raise ValueError("Too late to cancel a confirmed appointment.")

        self._status = AppointmentStatus.CANCELLED
class AppointmentLog:
    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._file = None

    def __enter__(self):
        self._file = open(self._filename, "a", encoding="utf-8")
        print("[log] opened")
        return self

    def write(self, message: str) -> None:
        if self._file is None:
            raise RuntimeError("The log is not open.")

        self._file.write(message + "\n")
        self._file.flush()

    def __exit__(self, error_type, error, traceback):
        file_to_close = self._file
        self._file = None

        if file_to_close is not None:
            try:
                file_to_close.close()
            finally:
                print("[log] closed")

        return False


def logged_action(action_name: str):
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            label = action_name

            if action_name in ("book", "confirm","cancel") and args:
                label = f"{action_name} #{args[0]}"

            try:
                result = method(self, *args, **kwargs)
            except Exception as error:
                self._log.write(f"FAILED {label}: {error}")
                raise

            self._log.write(f"{label}: SUCCESS")
            return result

        return wrapper

    return decorator
# Clinic rules:
# - It owns the registered patients, staff, and appointments.
# - Code outside the Clinic must not be able to change its internal lists.
class Clinic:
    def __init__(self, clock: Clock, log: AppointmentLog) -> None:
        self._clock = clock
        self._log = log
        self._patients: list[Patient] = []
        self._staff: list[Staff] = []
        self._used_ids: set[int] = set()
        self._appointments: list[Appointment] = []
        self._waiting_lists: dict[int, list[Patient]] = {}

    @property
    def patients(self) -> tuple[Patient, ...]:
        return tuple(self._patients)

    @property
    def staff(self) -> tuple[Staff, ...]:
        return tuple(self._staff)

    @property
    def appointments(self) -> tuple[Appointment, ...]:
        return tuple(self._appointments)

    def _ensure_id_available(self, object_id: int) -> None:
        if object_id in self._used_ids:
            raise ValueError("This ID is already in use.")
    @logged_action("register patient")
    def register_patient(self, patient: Patient) -> None:
        self._ensure_id_available(patient.person_id)
        self._patients.append(patient)
        self._used_ids.add(patient.person_id)

    def register_staff(self, staff_member: Staff) -> None:
        self._ensure_id_available(staff_member.person_id)
        self._staff.append(staff_member)
        self._used_ids.add(staff_member.person_id)
    def join_waiting_list(self, patient: Patient, staff_member: Staff) -> None:
        if patient not in self._patients:
            raise ValueError("Patient is not registered.")

        if staff_member not in self._staff:
            raise ValueError("Staff member is not registered.")

        waiting_patient_ids = [
            waiting_patient.person_id
            for waiting_patient in self._waiting_lists.get(staff_member.person_id, [])
        ]

        if patient.person_id in waiting_patient_ids:
            raise ValueError("Patient is already on this waiting list.")

        self._waiting_lists.setdefault(staff_member.person_id, []).append(patient)

    @logged_action("book")
    def book_appointment(
        self,
        appointment_id: int,
        patient: Patient,
        staff_member: Staff,
        start_hour: int,
    ) -> Appointment:
        if patient not in self._patients:
            raise ValueError("Patient is not registered.")

        if staff_member not in self._staff:
            raise ValueError("Staff member is not registered.")

        self._ensure_id_available(appointment_id)

        for existing in self._appointments:
            if (
                existing.start_hour == start_hour
                and existing.status != AppointmentStatus.CANCELLED
                and (
                    existing.patient.person_id == patient.person_id
                    or existing.staff.person_id == staff_member.person_id
                )
            ):
                raise ValueError("Patient or staff member already has an appointment then.")

        appointment = Appointment(
            appointment_id,
            patient,
            staff_member,
            start_hour,
            self._clock,
        )
        self._appointments.append(appointment)
        self._used_ids.add(appointment_id)
        return appointment

    def _next_available_id(self) -> int:
        candidate = 1
        while candidate in self._used_ids:
            candidate = candidate + 1
        return candidate

    def _offer_slot_to_waiting_patient(self, cancelled_appointment: Appointment) -> None:
        staff_id = cancelled_appointment.staff.person_id
        waiting_list = self._waiting_lists.get(staff_id, [])

        for waiting_patient in waiting_list.copy():
            try:
                self.book_appointment(
                    self._next_available_id(),
                    waiting_patient,
                    cancelled_appointment.staff,
                    cancelled_appointment.start_hour,
                )
            except ValueError:
                continue
            waiting_list.remove(waiting_patient)
            return

    @logged_action("cancel")
    def cancel_appointment(self, appointment_id: int) -> Appointment:
        for appointment in self._appointments:
            if appointment.appointment_id == appointment_id:
                appointment.cancel()
                self._offer_slot_to_waiting_patient(appointment)
                return appointment

        raise ValueError("Appointment was not found.")

    @logged_action("confirm")
    def confirm_appointment(self, appointment_id: int) -> Appointment:
        for appointment in self._appointments:
            if appointment.appointment_id == appointment_id:
                appointment.confirm()
                return appointment

        raise ValueError("Appointment was not found.")


if __name__ == "__main__":
    with AppointmentLog("appointments.log") as log:
        clock = ManualClock(10)
        clinic = Clinic(clock, log)

        first_patient = Patient("Ava", 1)
        waiting_patient = Patient("Ben", 2)
        doctor = Doctor("Dr. Ncube", 3)
        nurse = Nurse("Nurse Moyo", 6)
        pharmacist = Pharmacist("Pharmacist Dube", 7)

        # Show that Person's constructor runs once for this object.
        before = Person.constructor_calls
        medical_lecturer = MedicalLecturer("Dr. Tariro", 50, "Public Health")
        after = Person.constructor_calls
        print("Person constructor calls:", after - before)

        # Register everyone with the clinic.
        clinic.register_patient(first_patient)
        clinic.register_patient(waiting_patient)
        clinic.register_staff(doctor)
        clinic.register_staff(nurse)
        clinic.register_staff(pharmacist)
        clinic.register_staff(medical_lecturer)

        # One loop works for every kind of staff member.
        for staff_member in clinic.staff:
            print(staff_member.role(), "fee:", staff_member.fee())

        # Book and confirm an appointment for hour 15.
        clinic.book_appointment(4, first_patient, doctor, 15)
        clinic.join_waiting_list(waiting_patient, doctor)
        clinic.confirm_appointment(4)

        # Deliberately try to double-book Ava with the same doctor and hour.
        try:
            clinic.book_appointment(99, first_patient, doctor, 15)
        except ValueError as error:
            print("Expected booking failure:", error)

        # Cancel the appointment. Ben should receive the freed slot as PENDING.
        clinic.cancel_appointment(4)
        print("Waiting patient appointment:", clinic.appointments[-1].status.value)