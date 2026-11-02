import contextlib
import io
import pathlib
import unittest

from main import (
    P,
    AppointmentLog,
    AppointmentStatus,
    Clinic,
    Doctor,
    LogError,
    ManualClock,
    MedicalLecturer,
    Nurse,
    Patient,
    Person,
    Pharmacist,
    Staff,
)


class MemoryLog:
    """Stands in for AppointmentLog in tests: just remembers the lines."""

    def __init__(self) -> None:
        self.lines = []

    def write(self, message: str) -> None:
        self.lines.append(message)


class FakeFile:
    def __init__(self, fail_write=False, fail_close=False) -> None:
        self.fail_write = fail_write
        self.fail_close = fail_close
        self.lines = []
        self.close_calls = 0

    def write(self, text):
        if self.fail_write:
            raise OSError("disk full")
        self.lines.append(text)

    def flush(self):
        pass

    def close(self):
        self.close_calls += 1
        if self.fail_close:
            raise OSError("disk unplugged")


class FakeOpener:
    def __init__(self, fake_file) -> None:
        self.fake_file = fake_file
        self.open_calls = 0

    def __call__(self, path, mode, encoding=None):
        self.open_calls += 1
        return self.fake_file


class ClinicTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ManualClock(10)
        self.log = MemoryLog()
        self.clinic = Clinic(self.clock, self.log)

        self.ava = Patient("Ava", 1)
        self.ben = Patient("Ben", 2)
        self.chipo = Patient("Chipo", 8)
        self.doctor = Doctor("Dr. Ncube", 3)
        self.nurse = Nurse("Nurse Moyo", 6)

        for patient in (self.ava, self.ben, self.chipo):
            self.clinic.register_patient(patient)
        for staff_member in (self.doctor, self.nurse):
            self.clinic.register_staff(staff_member)


class ConstructorTests(unittest.TestCase):
    def test_empty_and_blank_names_are_rejected(self):
        for bad_name in ("", "   ", None):
            with self.assertRaises(ValueError):
                Patient(bad_name, 1)

    def test_non_positive_and_non_whole_ids_are_rejected(self):
        for bad_id in (0, -1, 2.5, "3", None, True):
            with self.assertRaises(ValueError):
                Doctor("Dr. X", bad_id)

    def test_lecturer_needs_a_module_name(self):
        with self.assertRaises(ValueError):
            MedicalLecturer("Dr. X", 5, "  ")


class FeeAndPolymorphismTests(unittest.TestCase):
    def test_fees_follow_the_formulas(self):
        self.assertEqual(Doctor("D", 1).fee(), 40 + 5 * (P % 5))
        self.assertEqual(Nurse("N", 2).fee(), 10 + (P % 3))
        self.assertEqual(Pharmacist("Ph", 3).fee(), 5)

    def test_medical_lecturer_charges_the_doctor_fee(self):
        self.assertEqual(MedicalLecturer("ML", 4, "Anatomy").fee(), Doctor("D", 1).fee())

    def test_new_staff_subclass_needs_no_changes_to_clinic_or_loop(self):
        class Physiotherapist(Staff):  # brand-new class, nothing else edited
            def role(self):
                return "Physiotherapist"

            def fee(self):
                return 25

        clinic = Clinic(ManualClock(0), MemoryLog())
        clinic.register_staff(Physiotherapist("Physio Gumbo", 9))
        clinic.register_patient(Patient("Ava", 1))
        clinic.book_appointment(10, clinic.patients[0], clinic.staff[0], 5)

        printed = [(s.role(), s.fee()) for s in clinic.staff]
        self.assertEqual(printed, [("Physiotherapist", 25)])

    def test_source_has_no_type_checks(self):
        source = pathlib.Path(__file__).with_name("main.py").read_text(encoding="utf-8")
        self.assertNotIn("isinstance(", source)
        self.assertNotIn("type(", source)


class MedicalLecturerTests(unittest.TestCase):
    def test_person_constructor_runs_once(self):
        before = Person.constructor_calls
        lecturer = MedicalLecturer("Dr. Tariro", 50, "Public Health")
        self.assertEqual(Person.constructor_calls - before, 1)
        self.assertEqual(lecturer.role(), "Doctor and Lecturer")
        self.assertEqual(lecturer.module_name, "Public Health")
        self.assertEqual(MedicalLecturer.__mro__.count(Person), 1)


class EncapsulationTests(ClinicTestCase):
    def test_lists_are_handed_out_as_read_only_copies(self):
        with self.assertRaises(AttributeError):
            self.clinic.patients.append(Patient("Intruder", 99))
        self.assertEqual(len(self.clinic.patients), 3)

    def test_appointment_status_cannot_be_changed_from_outside(self):
        appointment = self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.assertFalse(hasattr(appointment, "cancel"))
        self.assertFalse(hasattr(appointment, "confirm"))
        with self.assertRaises(AttributeError):
            appointment.status = AppointmentStatus.CANCELLED


class StatusTransitionTests(ClinicTestCase):
    def test_pending_can_be_confirmed_then_cancelled_with_notice(self):
        appointment = self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.assertEqual(appointment.status, AppointmentStatus.PENDING)
        self.clinic.confirm_appointment(20)
        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)
        self.clinic.cancel_appointment(20)
        self.assertEqual(appointment.status, AppointmentStatus.CANCELLED)

    def test_cancelled_never_comes_back(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.clinic.cancel_appointment(20)
        with self.assertRaises(ValueError):
            self.clinic.confirm_appointment(20)
        with self.assertRaises(ValueError):
            self.clinic.cancel_appointment(20)

    def test_confirmed_cannot_be_confirmed_again(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.clinic.confirm_appointment(20)
        with self.assertRaises(ValueError):
            self.clinic.confirm_appointment(20)

    def test_confirmed_needs_two_hours_notice(self):
        appointment = self.clinic.book_appointment(20, self.ava, self.doctor, 13)
        self.clinic.confirm_appointment(20)
        self.clock.set(12)  # 1 hour before
        with self.assertRaises(ValueError) as caught:
            self.clinic.cancel_appointment(20)
        self.assertIn("too late", str(caught.exception))
        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)

    def test_confirmed_can_be_cancelled_exactly_two_hours_before(self):
        appointment = self.clinic.book_appointment(20, self.ava, self.doctor, 13)
        self.clinic.confirm_appointment(20)
        self.clock.set(11)
        self.clinic.cancel_appointment(20)
        self.assertEqual(appointment.status, AppointmentStatus.CANCELLED)

    def test_pending_can_be_cancelled_one_hour_before(self):
        appointment = self.clinic.book_appointment(20, self.ava, self.doctor, 13)
        self.clock.set(12)
        self.clinic.cancel_appointment(20)
        self.assertEqual(appointment.status, AppointmentStatus.CANCELLED)

    def test_nothing_can_be_cancelled_once_started(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 13)
        for now in (13, 14):
            self.clock.set(now)
            with self.assertRaises(ValueError) as caught:
                self.clinic.cancel_appointment(20)
            self.assertIn("already started", str(caught.exception))


class BookingRuleTests(ClinicTestCase):
    def test_staff_cannot_be_double_booked(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        with self.assertRaises(ValueError):
            self.clinic.book_appointment(21, self.ben, self.doctor, 15)

    def test_patient_cannot_be_double_booked_with_another_staff_member(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        with self.assertRaises(ValueError):
            self.clinic.book_appointment(21, self.ava, self.nurse, 15)

    def test_cancelled_appointment_frees_the_hour(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.clinic.cancel_appointment(20)
        self.clinic.book_appointment(21, self.ava, self.doctor, 15)

    def test_ids_are_unique_across_the_whole_clinic(self):
        with self.assertRaises(ValueError):
            self.clinic.register_patient(Patient("Copy", 3))  # 3 is the doctor
        with self.assertRaises(ValueError):
            self.clinic.book_appointment(1, self.ben, self.nurse, 15)  # 1 is Ava
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        with self.assertRaises(ValueError):
            self.clinic.book_appointment(20, self.ben, self.nurse, 16)

    def test_cannot_book_a_started_or_impossible_hour(self):
        for bad_hour in (9, 10, 168, -1):
            with self.assertRaises(ValueError):
                self.clinic.book_appointment(20, self.ava, self.doctor, bad_hour)

    def test_unregistered_people_cannot_book(self):
        with self.assertRaises(ValueError):
            self.clinic.book_appointment(20, Patient("Stranger", 40), self.doctor, 15)

    def test_failed_booking_leaves_no_trace_except_the_log(self):
        with self.assertRaises(ValueError):
            self.clinic.book_appointment(20, self.ava, self.doctor, 9)
        self.assertEqual(self.clinic.appointments, ())
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)  # id 20 still free


class LoggingTests(ClinicTestCase):
    def test_successes_and_failures_are_logged(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 11)
        self.clinic.confirm_appointment(20)
        with self.assertRaises(ValueError):
            self.clinic.cancel_appointment(20)

        self.assertIn("book #20: OK", self.log.lines)
        self.assertIn("confirm #20: OK", self.log.lines)
        self.assertTrue(
            any(line.startswith("FAILED cancel #20: too late") for line in self.log.lines)
        )

    def test_registration_is_logged(self):
        self.assertIn("register staff Dr. Ncube (id 3): OK", self.log.lines)


class WaitingListTests(ClinicTestCase):
    def test_slot_goes_to_first_waiting_patient(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.clinic.join_waiting_list(self.ben, self.doctor)
        self.clinic.cancel_appointment(20)

        offered = self.clinic.appointments[-1]
        self.assertEqual(offered.patient, self.ben)
        self.assertEqual(offered.start_hour, 15)
        self.assertEqual(offered.status, AppointmentStatus.PENDING)
        self.assertEqual(self.clinic.waiting_list(self.doctor), ())
        self.assertTrue(any(line.startswith("OFFERED") for line in self.log.lines))

    def test_offer_is_logged_after_the_cancel(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.clinic.join_waiting_list(self.ben, self.doctor)
        self.clinic.cancel_appointment(20)
        cancel_line = self.log.lines.index("cancel #20: OK")
        offer_line = next(i for i, line in enumerate(self.log.lines) if line.startswith("OFFERED"))
        self.assertLess(cancel_line, offer_line)

    def test_busy_waiting_patient_is_skipped(self):
        self.clinic.book_appointment(20, self.ava, self.doctor, 15)
        self.clinic.book_appointment(21, self.ben, self.nurse, 15)  # Ben is busy at 15
        self.clinic.join_waiting_list(self.ben, self.doctor)
        self.clinic.join_waiting_list(self.chipo, self.doctor)
        self.clinic.cancel_appointment(20)

        offered = self.clinic.appointments[-1]
        self.assertEqual(offered.patient, self.chipo)
        self.assertEqual(self.clinic.waiting_list(self.doctor), (self.ben,))

    def test_cannot_join_the_same_waiting_list_twice(self):
        self.clinic.join_waiting_list(self.ben, self.doctor)
        with self.assertRaises(ValueError):
            self.clinic.join_waiting_list(self.ben, self.doctor)


class AppointmentLogTests(unittest.TestCase):
    def run_quietly(self, action):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            action()
        return output.getvalue()

    def test_opened_and_closed_exactly_once_even_after_an_error(self):
        fake = FakeFile()
        opener = FakeOpener(fake)

        def crash_inside():
            with self.assertRaises(RuntimeError):
                with AppointmentLog("x.log", opener=opener, echo=False) as log:
                    log.write("before crash")
                    raise RuntimeError("boom")

        output = self.run_quietly(crash_inside)
        self.assertEqual(opener.open_calls, 1)
        self.assertEqual(fake.close_calls, 1)
        self.assertEqual(output.count("[log] opened"), 1)
        self.assertEqual(output.count("[log] closed"), 1)

    def test_log_cannot_be_opened_twice(self):
        log = AppointmentLog("x.log", opener=FakeOpener(FakeFile()), echo=False)

        def use_twice():
            with log:
                pass
            with self.assertRaises(LogError):
                with log:
                    pass

        self.run_quietly(use_twice)

    def test_failed_close_does_not_hide_the_original_error(self):
        opener = FakeOpener(FakeFile(fail_close=True))

        def crash_inside():
            with self.assertRaises(RuntimeError):
                with AppointmentLog("x.log", opener=opener, echo=False):
                    raise RuntimeError("original problem")

        self.run_quietly(crash_inside)

    def test_failed_close_without_other_errors_is_reported(self):
        opener = FakeOpener(FakeFile(fail_close=True))

        def close_fails():
            with self.assertRaises(LogError):
                with AppointmentLog("x.log", opener=opener, echo=False):
                    pass

        self.run_quietly(close_fails)

    def test_failed_write_is_reported(self):
        opener = FakeOpener(FakeFile(fail_write=True))

        def write_fails():
            with AppointmentLog("x.log", opener=opener, echo=False) as log:
                with self.assertRaises(LogError):
                    log.write("hello")

        self.run_quietly(write_fails)

    def test_writing_after_close_fails(self):
        log = AppointmentLog("x.log", opener=FakeOpener(FakeFile()), echo=False)

        def write_late():
            with log:
                pass
            with self.assertRaises(LogError):
                log.write("too late")

        self.run_quietly(write_late)


if __name__ == "__main__":
    unittest.main()
