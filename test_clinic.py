"""
test_clinic.py - Unit test suite for the Clinic Appointment System.

Tests all aspects of the specification:
1. Time constraints & Clock object behavior (0 to 168 hours)
2. Constructor validation (non-empty strings, positive IDs)
3. Encapsulation (immutability of internal lists)
4. Polymorphism & fee formulas for Doctor, Nurse, Pharmacist
5. Appointment state transitions & cancellation rules (cannot return, < 2 hours, already started)
6. Logging context manager (opened/closed guarantee, logging failures)
7. Multiple inheritance (MedicalLecturer, Person called once, fee return value)
8. Scheduling rules (no duplicate IDs, no overlapping non-cancelled appointments)
9. Twist 0: FIFO waiting list & automatic slot offer upon cancellation
"""

import unittest
from clock import Clock
from models import (
    Person, Patient, Staff, Doctor, Nurse, Pharmacist,
    Lecturer, MedicalLecturer, Appointment,
    STUDENT_ID, DOCTOR_BASE_FEE, NURSE_BASE_FEE, PHARMACIST_FEE
)
from clinic import Clinic


class TestClinicAppointmentSystem(unittest.TestCase):

    def setUp(self):
        # Fresh clock starting at hour 0
        self.clock = Clock(start_hour=0)
        self.clinic = Clinic(name="Test Clinic", clock=self.clock)

    # =================================================================
    # 1. Clock & Time Tests
    # =================================================================
    def test_clock_valid_bounds(self):
        c = Clock(0)
        self.assertEqual(c.now(), 0)
        c.advance(10)
        self.assertEqual(c.now(), 10)
        c.set_time(168)
        self.assertEqual(c.now(), 168)

    def test_clock_invalid_hours(self):
        with self.assertRaises(ValueError):
            Clock(-1)
        with self.assertRaises(ValueError):
            Clock(169)
        c = Clock(160)
        with self.assertRaises(ValueError):
            c.advance(10)  # Exceeds 168

    # =================================================================
    # 2. Constructor Validations
    # =================================================================
    def test_person_validation(self):
        # Valid
        p = Patient(patient_id=1, name="John Smith")
        self.assertEqual(p.id, 1)
        self.assertEqual(p.name, "John Smith")

        # Zero or negative ID
        with self.assertRaises(ValueError):
            Patient(patient_id=0, name="Valid Name")
        with self.assertRaises(ValueError):
            Patient(patient_id=-1, name="Valid Name")

        # Empty or whitespace name
        with self.assertRaises(ValueError):
            Patient(patient_id=2, name="")
        with self.assertRaises(ValueError):
            Patient(patient_id=2, name="   ")

    # =================================================================
    # 3. Encapsulation Tests
    # =================================================================
    def test_encapsulation_copy_protection(self):
        p = Patient(patient_id=10, name="Alice")
        self.clinic.register_person(p)

        # External modification must not affect clinic internal state
        pts = self.clinic.get_patients()
        self.assertEqual(len(pts), 1)
        pts.clear()
        self.assertEqual(len(self.clinic.get_patients()), 1)

    # =================================================================
    # 4. Polymorphic Fees & Roles
    # =================================================================
    def test_staff_fees_and_roles(self):
        doc = Doctor(staff_id=1, name="Dr. A")
        nurse = Nurse(staff_id=2, name="Nurse B")
        pharm = Pharmacist(staff_id=3, name="Pharm C")

        self.assertEqual(doc.role(), "Doctor")
        self.assertEqual(doc.fee(), DOCTOR_BASE_FEE)
        self.assertEqual(doc.fee(), 40)

        self.assertEqual(nurse.role(), "Nurse")
        self.assertEqual(nurse.fee(), NURSE_BASE_FEE)
        self.assertEqual(nurse.fee(), 12)

        self.assertEqual(pharm.role(), "Pharmacist")
        self.assertEqual(pharm.fee(), 5)

    # =================================================================
    # 5. Appointment Lifecycle & Cancellation Rules
    # =================================================================
    def test_appointment_lifecycle(self):
        pt = Patient(patient_id=1, name="Patient 1")
        doc = Doctor(staff_id=2, name="Doctor 1")
        appt = Appointment(appt_id=100, patient=pt, staff=doc, start_hour=10)

        self.assertEqual(appt.status, Appointment.STATUS_PENDING)
        appt.confirm()
        self.assertEqual(appt.status, Appointment.STATUS_CONFIRMED)

        # Cannot confirm again
        with self.assertRaises(ValueError):
            appt.confirm()

        # Cannot cancel less than 2 hours before start when CONFIRMED
        with self.assertRaises(ValueError):
            appt.cancel(current_hour=9)  # 1 hour remaining

        # Cancellation allowed >= 2 hours before start
        appt.cancel(current_hour=8)  # 2 hours remaining
        self.assertEqual(appt.status, Appointment.STATUS_CANCELLED)

        # Rule: Cancelled appointment can NEVER return or be re-cancelled
        with self.assertRaises(ValueError):
            appt.confirm()
        with self.assertRaises(ValueError):
            appt.cancel(current_hour=5)

    def test_cannot_cancel_after_started(self):
        pt = Patient(patient_id=1, name="Patient 1")
        doc = Doctor(staff_id=2, name="Doctor 1")
        appt = Appointment(appt_id=200, patient=pt, staff=doc, start_hour=10)

        # At start hour or after
        with self.assertRaises(ValueError):
            appt.cancel(current_hour=10)
        with self.assertRaises(ValueError):
            appt.cancel(current_hour=11)

    # =================================================================
    # 6. Logging Guarantee
    # =================================================================
    def test_logging_guarantee_and_failure_logging(self):
        pt = Patient(patient_id=1, name="Patient 1")
        doc = Doctor(staff_id=2, name="Doctor 1")
        self.clinic.register_person(pt)
        self.clinic.register_person(doc)

        self.clock.set_time(5)
        self.clinic.book_appointment(appt_id=50, patient=pt, staff=doc, start_hour=7)
        self.clinic.confirm_appointment(appt_id=50)

        # Advance to 6 (1 hour before start) -> Cancellation should fail with "too late"
        self.clock.set_time(6)
        result = self.clinic.cancel_appointment(appt_id=50)
        self.assertFalse(result)

        history = self.clinic.get_log_history()
        self.assertIn("[log] opened", history)
        self.assertIn("[log] closed", history)
        self.assertTrue(any("FAILED cancel #50: too late" in entry for entry in history))

    # =================================================================
    # 7. Multiple Inheritance (MedicalLecturer)
    # =================================================================
    def test_medical_lecturer_diamond_problem(self):
        Person.constructor_count = 0
        med_lec = MedicalLecturer(person_id=88, name="Dr. Watson", module_name="Cardiology")

        # Invariant: Person constructor must run exactly once
        self.assertEqual(Person.constructor_count, 1)
        self.assertEqual(med_lec.role(), "Doctor and Lecturer")
        self.assertEqual(med_lec.fee(), 40)
        self.assertEqual(med_lec.module_name, "Cardiology")
        self.assertEqual(med_lec.id, 88)
        self.assertEqual(med_lec.name, "Dr. Watson")

    # =================================================================
    # 8. Unique IDs & Overlapping Booking Prevention
    # =================================================================
    def test_unique_person_ids(self):
        p1 = Patient(patient_id=10, name="Alice")
        p2 = Doctor(staff_id=10, name="Dr. Bob")
        self.clinic.register_person(p1)
        with self.assertRaises(ValueError):
            self.clinic.register_person(p2)

    def test_overlapping_appointment_prevention(self):
        p1 = Patient(patient_id=1, name="Alice")
        p2 = Patient(patient_id=2, name="Bob")
        doc = Doctor(staff_id=10, name="Dr. Charlie")

        self.clinic.register_person(p1)
        self.clinic.register_person(p2)
        self.clinic.register_person(doc)

        # Book p1 with doc at hour 15
        appt1 = self.clinic.book_appointment(appt_id=1, patient=p1, staff=doc, start_hour=15)
        self.assertIsNotNone(appt1)

        # Attempt to book p2 with doc at same hour 15 -> Must fail
        appt2 = self.clinic.book_appointment(appt_id=2, patient=p2, staff=doc, start_hour=15)
        self.assertIsNone(appt2)

        # Attempt to book p1 with another doctor at same hour 15 -> Must fail
        doc2 = Doctor(staff_id=20, name="Dr. Donna")
        self.clinic.register_person(doc2)
        appt3 = self.clinic.book_appointment(appt_id=3, patient=p1, staff=doc2, start_hour=15)
        self.assertIsNone(appt3)

    # =================================================================
    # 9. Twist 0: Waiting List & Auto-Offer
    # =================================================================
    def test_twist_0_waiting_list_auto_offer(self):
        p_original = Patient(patient_id=1, name="Original Patient")
        p_waiting_1 = Patient(patient_id=2, name="Waitlist First")
        p_waiting_2 = Patient(patient_id=3, name="Waitlist Second")
        doc = Doctor(staff_id=10, name="Dr. Specialist")

        self.clinic.register_person(p_original)
        self.clinic.register_person(p_waiting_1)
        self.clinic.register_person(p_waiting_2)
        self.clinic.register_person(doc)

        # Book appointment at hour 20 (current clock is 0)
        self.clinic.book_appointment(appt_id=1, patient=p_original, staff=doc, start_hour=20)

        # Patients join waitlist for doctor
        self.clinic.join_waiting_list(p_waiting_1, doc)
        self.clinic.join_waiting_list(p_waiting_2, doc)
        self.assertEqual(len(self.clinic.get_waiting_list(doc)), 2)

        # Cancel original appointment > 2 hours ahead
        success = self.clinic.cancel_appointment(appt_id=1)
        self.assertTrue(success)

        # Check that slot was auto-offered to p_waiting_1
        waitlist_after = self.clinic.get_waiting_list(doc)
        self.assertEqual(len(waitlist_after), 1)
        self.assertEqual(waitlist_after[0].id, p_waiting_2.id)

        # Find the newly created appointment
        all_appts = self.clinic.get_appointments()
        offered_appt = [a for a in all_appts if a.id != 1][0]
        self.assertEqual(offered_appt.patient.id, p_waiting_1.id)
        self.assertEqual(offered_appt.staff.id, doc.id)
        self.assertEqual(offered_appt.start_hour, 20)
        self.assertEqual(offered_appt.status, Appointment.STATUS_PENDING)


if __name__ == "__main__":
    unittest.main()
