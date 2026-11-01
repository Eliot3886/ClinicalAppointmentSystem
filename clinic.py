"""
clinic.py - Clinic management and logging for the Clinic Appointment System.

Demonstrates:
- ClinicLogger context manager guaranteeing [log] opened and [log] closed are printed
- Strict scheduling rules (no overlapping appointments for staff or patient)
- Unique IDs across the clinic
- Encapsulation (preventing external modification of internal lists)
- Twist 0 (Waiting list with automatic offer on cancellation)
"""

from typing import List, Dict, Optional
from clock import Clock
from models import Person, Patient, Staff, Appointment


class ClinicActionLogger:
    """
    Context manager that guarantees the appointment log is opened and closed
    exactly once per operation, even if an unexpected exception occurs mid-operation.
    Uses Python's context management protocol (__enter__ and __exit__) and try...finally.
    """

    def __init__(self, clinic: "Clinic", action_description: str):
        self._clinic = clinic
        self._action = action_description
        self._opened = False

    def __enter__(self):
        self._clinic._write_raw_log("[log] opened")
        self._opened = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # If an unhandled exception occurred inside the with block, log it as FAILED
            if exc_type is not None and exc_val is not None:
                self._clinic._write_raw_log(f"[log] FAILED {self._action}: {exc_val}")
        finally:
            # Guarantee that [log] closed is ALWAYS printed and recorded
            self._clinic._write_raw_log("[log] closed")
        # Return False so any exception is propagated if needed, or True to suppress
        return False


# =====================================================================
# Clinic Class
# =====================================================================
# INVARIANTS of Clinic:
# 1. Person IDs are globally unique across all registered patients and staff.
# 2. Appointment IDs are strictly unique across all appointments in the clinic.
# 3. No staff member may have two non-cancelled appointments at the same hour.
# 4. No patient may have two non-cancelled appointments at the same hour.
# 5. Clinic never reads the system clock; it exclusively relies on an injected Clock instance.
# 6. Encapsulation: Methods never hand out internal mutable lists or dicts;
#    all accessors return fresh shallow copies (e.g., list(self._...)).
# 7. Every clinic action guarantees that [log] opened and [log] closed are recorded
#    via the ClinicActionLogger context manager.
# 8. Twist 0 (Waiting list): Each staff member maintains a FIFO waiting list of patients.
#    When an appointment is cancelled, the first waiting patient with no conflict
#    is automatically allocated the slot as a new PENDING appointment.
class Clinic:
    """
    Coordinates patients, staff, appointments, scheduling rules, and waiting lists.
    """

    def __init__(self, name: str, clock: Clock):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Clinic name cannot be empty.")
        if not isinstance(clock, Clock):
            raise TypeError("Clinic requires a valid Clock instance.")

        self._name = name.strip()
        self._clock = clock

        # Encapsulated internal storage: private dictionaries keyed by ID
        self._persons: Dict[int, Person] = {}
        self._patients: Dict[int, Patient] = {}
        self._staff: Dict[int, Staff] = {}
        self._appointments: Dict[int, Appointment] = {}

        # Twist 0: Waiting lists mapped per staff_id -> list of Patient objects
        self._waiting_lists: Dict[int, List[Patient]] = {}

        # Audit log storage
        self._log_history: List[str] = []

        # Internal counter for generating unique IDs if needed
        self._next_auto_id = 9000

    @property
    def name(self) -> str:
        return self._name

    @property
    def clock(self) -> Clock:
        return self._clock

    # =================================================================
    # Encapsulation Accessors: Always return COPIES of internal lists
    # =================================================================
    def get_patients(self) -> List[Patient]:
        """Return a copy of the list of registered patients."""
        return list(self._patients.values())

    def get_staff(self) -> List[Staff]:
        """Return a copy of the list of registered staff."""
        return list(self._staff.values())

    def get_appointments(self) -> List[Appointment]:
        """Return a copy of all appointments."""
        return list(self._appointments.values())

    def get_log_history(self) -> List[str]:
        """Return a copy of the recorded log history."""
        return list(self._log_history)

    def get_waiting_list(self, staff: Staff) -> List[Patient]:
        """Return a copy of the waiting list for a given staff member."""
        if staff.id not in self._waiting_lists:
            return []
        return list(self._waiting_lists[staff.id])

    # =================================================================
    # Logging helper
    # =================================================================
    def _write_raw_log(self, message: str) -> None:
        """Internal method to write and print log entries."""
        print(message)
        self._log_history.append(message)

    def log_action(self, action_name: str) -> ClinicActionLogger:
        """Create a context manager for logging an operation."""
        return ClinicActionLogger(self, action_name)

    # =================================================================
    # Registration
    # =================================================================
    def register_person(self, person: Person) -> None:
        """
        Register a patient or staff member in the clinic.
        Enforces rule: person IDs must be unique across the entire clinic.
        """
        if not isinstance(person, Person):
            raise TypeError("Expected a Person instance.")

        if person.id in self._persons:
            raise ValueError(f"Person ID #{person.id} already exists in the clinic.")

        self._persons[person.id] = person

        if isinstance(person, Patient):
            self._patients[person.id] = person
        elif isinstance(person, Staff):
            self._staff[person.id] = person
            self._waiting_lists[person.id] = []

    # =================================================================
    # Appointment Scheduling
    # =================================================================
    def book_appointment(self, appt_id: int, patient: Patient, staff: Staff, start_hour: int) -> Optional[Appointment]:
        """
        Book a new appointment.
        Enforces:
        - Unique appointment ID across the clinic.
        - Patient and staff must be registered.
        - Start hour cannot be in the past (must be >= clock.now()).
        - Neither staff nor patient may have two non-cancelled appointments at the same hour.
        Guarantees [log] opened and [log] closed are printed, and failure is logged.
        """
        action_name = f"book #{appt_id}"
        with self.log_action(action_name):
            # Rule: Appointment ID must be unique
            if appt_id in self._appointments:
                err_msg = f"appointment #{appt_id} already exists"
                self._write_raw_log(f"[log] FAILED {action_name}: {err_msg}")
                return None

            # Rule: Check if patient is registered
            if patient.id not in self._patients:
                err_msg = f"patient #{patient.id} ({patient.name}) is not registered"
                self._write_raw_log(f"[log] FAILED {action_name}: {err_msg}")
                return None

            # Rule: Check if staff is registered
            if staff.id not in self._staff:
                err_msg = f"staff #{staff.id} ({staff.name}) is not registered"
                self._write_raw_log(f"[log] FAILED {action_name}: {err_msg}")
                return None

            # Rule: Cannot book in the past
            current_time = self._clock.now()
            if start_hour < current_time:
                err_msg = f"cannot book in the past (current hour: {current_time}, requested: {start_hour})"
                self._write_raw_log(f"[log] FAILED {action_name}: {err_msg}")
                return None

            # Rule: Staff cannot have another non-cancelled appointment at the same hour
            staff_conflict = self._find_conflict_for_staff(staff, start_hour)
            if staff_conflict is not None:
                err_msg = f"staff {staff.name} is already booked at hour {start_hour} (appt #{staff_conflict.id})"
                self._write_raw_log(f"[log] FAILED {action_name}: {err_msg}")
                return None

            # Rule: Patient cannot have another non-cancelled appointment at the same hour
            patient_conflict = self._find_conflict_for_patient(patient, start_hour)
            if patient_conflict is not None:
                err_msg = f"patient {patient.name} already has an appointment at hour {start_hour} (appt #{patient_conflict.id})"
                self._write_raw_log(f"[log] FAILED {action_name}: {err_msg}")
                return None

            # Create appointment
            try:
                appt = Appointment(appt_id=appt_id, patient=patient, staff=staff, start_hour=start_hour)
            except Exception as e:
                self._write_raw_log(f"[log] FAILED {action_name}: {e}")
                return None

            self._appointments[appt_id] = appt
            self._write_raw_log(
                f"[log] SUCCESS {action_name}: {patient.name} with {staff.name} at hour {start_hour} (PENDING)"
            )
            return appt

    def confirm_appointment(self, appt_id: int) -> bool:
        """
        Confirm a pending appointment.
        """
        action_name = f"confirm #{appt_id}"
        with self.log_action(action_name):
            if appt_id not in self._appointments:
                self._write_raw_log(f"[log] FAILED {action_name}: appointment does not exist")
                return False

            appt = self._appointments[appt_id]
            try:
                appt.confirm()
                self._write_raw_log(f"[log] SUCCESS {action_name}: appointment is now CONFIRMED")
                return True
            except Exception as e:
                self._write_raw_log(f"[log] FAILED {action_name}: {e}")
                return False

    def cancel_appointment(self, appt_id: int) -> bool:
        """
        Cancel an appointment following all business rules.
        If cancellation succeeds:
        - Executes Twist 0: automatically offers the freed slot to the first waiting patient
          with no schedule conflict as a new PENDING appointment.
        """
        action_name = f"cancel #{appt_id}"
        with self.log_action(action_name):
            if appt_id not in self._appointments:
                self._write_raw_log(f"[log] FAILED {action_name}: appointment does not exist")
                return False

            appt = self._appointments[appt_id]
            current_hour = self._clock.now()

            try:
                appt.cancel(current_hour=current_hour)
            except ValueError as e:
                # Capture specific failure reason (e.g., too late, already started)
                msg = str(e)
                if "less than 2 hours" in msg:
                    reason = "too late"
                elif "already started" in msg:
                    reason = "appointment already started"
                elif "already CANCELLED" in msg:
                    reason = "already cancelled"
                else:
                    reason = msg
                self._write_raw_log(f"[log] FAILED {action_name}: {reason}")
                return False

            self._write_raw_log(
                f"[log] SUCCESS {action_name}: appointment for {appt.patient.name} with {appt.staff.name} at hour {appt.start_hour} cancelled"
            )

            # -------------------------------------------------------------
            # Twist 0: Waiting List Slot Reallocation
            # -------------------------------------------------------------
            self._handle_waiting_list_reallocation(appt.staff, appt.start_hour)
            return True

    # =================================================================
    # Twist 0: Waiting List Logic
    # =================================================================
    def join_waiting_list(self, patient: Patient, staff: Staff) -> bool:
        """
        Twist 0: A patient can join a staff member's waiting list.
        """
        action_name = f"waitlist patient #{patient.id} for staff #{staff.id}"
        with self.log_action(action_name):
            if patient.id not in self._patients:
                self._write_raw_log(f"[log] FAILED {action_name}: patient not registered")
                return False
            if staff.id not in self._staff:
                self._write_raw_log(f"[log] FAILED {action_name}: staff not registered")
                return False

            queue = self._waiting_lists[staff.id]
            if patient in queue:
                self._write_raw_log(f"[log] FAILED {action_name}: patient already on waitlist")
                return False

            queue.append(patient)
            self._write_raw_log(
                f"[log] SUCCESS {action_name}: {patient.name} joined waitlist for {staff.name} (position {len(queue)})"
            )
            return True

    def _handle_waiting_list_reallocation(self, staff: Staff, slot_hour: int) -> None:
        """
        When a slot frees up, the Clinic automatically offers the slot to
        the first waiting patient with no conflict, as a new PENDING appointment, and logs it.
        """
        queue = self._waiting_lists.get(staff.id, [])
        if not queue:
            return  # No patients waiting for this staff member

        # Find first eligible patient without a schedule conflict at slot_hour
        candidate_patient: Optional[Patient] = None
        candidate_index: int = -1

        for i, patient in enumerate(queue):
            if self._find_conflict_for_patient(patient, slot_hour) is None:
                candidate_patient = patient
                candidate_index = i
                break

        if candidate_patient is not None:
            # Remove patient from queue (FIFO)
            queue.pop(candidate_index)

            # Generate unique appointment ID
            new_appt_id = self._generate_unique_appt_id()

            # Create new PENDING appointment
            new_appt = Appointment(
                appt_id=new_appt_id,
                patient=candidate_patient,
                staff=staff,
                start_hour=slot_hour
            )
            self._appointments[new_appt_id] = new_appt

            self._write_raw_log(
                f"[log] AUTO-OFFERED slot at hour {slot_hour} with {staff.name} "
                f"to waiting patient {candidate_patient.name} as appointment #{new_appt_id} (PENDING)"
            )

    def _generate_unique_appt_id(self) -> int:
        """Generate a guaranteed unique appointment ID."""
        while self._next_auto_id in self._appointments:
            self._next_auto_id += 1
        new_id = self._next_auto_id
        self._next_auto_id += 1
        return new_id

    # =================================================================
    # Conflict Checking Helpers
    # =================================================================
    def _find_conflict_for_staff(self, staff: Staff, hour: int) -> Optional[Appointment]:
        """Return non-cancelled appointment for staff at hour, or None."""
        for appt in self._appointments.values():
            if appt.staff.id == staff.id and appt.start_hour == hour and appt.status != Appointment.STATUS_CANCELLED:
                return appt
        return None

    def _find_conflict_for_patient(self, patient: Patient, hour: int) -> Optional[Appointment]:
        """Return non-cancelled appointment for patient at hour, or None."""
        for appt in self._appointments.values():
            if appt.patient.id == patient.id and appt.start_hour == hour and appt.status != Appointment.STATUS_CANCELLED:
                return appt
        return None
