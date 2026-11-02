import unittest

from main import (
    AppointmentStatus,
    Clinic,
    Doctor,
    ManualClock,
    MedicalLecturer,
    Patient,
    Person,
)


class QuietLog:
    def write(self, message: str) -> None:
        pass


class ClinicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ManualClock(10)
        self.clinic = Clinic(self.clock, QuietLog())

        self.patient = Patient("Ava", 1)
        self.waiting_patient = Patient("Ben", 2)
        self.doctor = Doctor("Dr. Ncube", 3)

        self.clinic.register_patient(self.patient)
        self.clinic.register_patient(self.waiting_patient)
        self.clinic.register_staff(self.doctor)

    def test_same_staff_cannot_be_booked_twice_at_the_same_hour(self) -> None:
        self.clinic.book_appointment(4, self.patient, self.doctor, 15)

        with self.assertRaises(ValueError):
            self.clinic.book_appointment(
                5, self.waiting_patient, self.doctor, 15
            )

    def test_confirmed_appointment_cannot_be_cancelled_one_hour_before(self) -> None:
        appointment = self.clinic.book_appointment(
            4, self.patient, self.doctor, 11
        )
        self.clinic.confirm_appointment(4)

        with self.assertRaises(ValueError):
            self.clinic.cancel_appointment(4)

        self.assertEqual(appointment.status, AppointmentStatus.CONFIRMED)

    def test_cancelled_slot_is_offered_to_waiting_patient(self) -> None:
        self.clinic.book_appointment(4, self.patient, self.doctor, 15)
        self.clinic.join_waiting_list(self.waiting_patient, self.doctor)
        self.clinic.confirm_appointment(4)

        self.clinic.cancel_appointment(4)

        offered_appointment = self.clinic.appointments[-1]
        self.assertEqual(offered_appointment.patient.person_id, 2)
        self.assertEqual(offered_appointment.status, AppointmentStatus.PENDING)

    def test_medical_lecturer_initializes_person_once(self) -> None:
        before = Person.constructor_calls

        lecturer = MedicalLecturer("Dr. Tariro", 50, "Public Health")

        self.assertEqual(Person.constructor_calls - before, 1)
        self.assertEqual(lecturer.role(), "Doctor and Lecturer")


if __name__ == "__main__":
    unittest.main()