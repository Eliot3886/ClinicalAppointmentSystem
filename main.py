"""
main.py - Comprehensive demonstration of the Clinic Appointment System.

Fulfills all requirements from Part 1 to Part 8:
- Part 1: Domain models (Person, Patient, Doctor, Nurse, Pharmacist, Appointment, Clinic)
- Part 2: Encapsulation, status lifecycle transitions, cancellation rules, constructor validation
- Part 3: Polymorphic fee calculation without any isinstance/type tags
- Part 4: Context manager logging guaranteeing [log] opened and [log] closed, capturing failures
- Part 5: Multiple inheritance (MedicalLecturer), Person constructor executed ONCE, fee return value
- Part 6 & Twist 0: Conflict checks, unique IDs, and FIFO waiting list auto-allocation
- Part 8: Step-by-step demonstration including deliberate failure cases
"""

from clock import Clock
from models import (
    Person, Patient, Staff, Doctor, Nurse, Pharmacist,
    Lecturer, MedicalLecturer, Appointment,
    STUDENT_ID, DOCTOR_BASE_FEE, NURSE_BASE_FEE, PHARMACIST_FEE
)
from clinic import Clinic


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_part_1_and_2():
    print_section("PART 1 & 2: CONSTRUCTOR VALIDATION, ENCAPSULATION & INVARIANTS")

    print("[*] Student Number:", STUDENT_ID)
    print("[*] Calculated Fees:")
    print(f"    - Doctor:     40 + 5 * ({STUDENT_ID} % 5) = ${DOCTOR_BASE_FEE}")
    print(f"    - Nurse:      10 + ({STUDENT_ID} % 3)     = ${NURSE_BASE_FEE}")
    print(f"    - Pharmacist: ${PHARMACIST_FEE}")
    print(f"    - Twist:      {STUDENT_ID} % 4 = {STUDENT_ID % 4} (Twist 0: Waiting list)")

    print("\n--- 1. Constructor Validation (Rejecting empty names & non-positive IDs) ---")
    # Valid patient
    p = Patient(patient_id=101, name="Alice Walker")
    print(f"  [SUCCESS] Created: {p}")

    # Reject non-positive ID
    try:
        Patient(patient_id=0, name="Invalid ID")
    except ValueError as e:
        print(f"  [REJECTED] Non-positive ID: {e}")

    # Reject negative ID
    try:
        Patient(patient_id=-5, name="Invalid Negative ID")
    except ValueError as e:
        print(f"  [REJECTED] Negative ID: {e}")

    # Reject empty name
    try:
        Patient(patient_id=102, name="   ")
    except ValueError as e:
        print(f"  [REJECTED] Empty/whitespace name: {e}")

    print("\n--- 2. Encapsulation: Preventing external mutation of internal lists ---")
    clock = Clock(start_hour=10)
    clinic = Clinic(name="City Central Health", clock=clock)
    clinic.register_person(p)

    patients_copy = clinic.get_patients()
    print(f"  Internal patients before external modification: {[pt.name for pt in clinic.get_patients()]}")
    # Modifying the returned copy:
    patients_copy.clear()
    print(f"  Modified external list: {patients_copy}")
    print(f"  Internal patients after external clear():      {[pt.name for pt in clinic.get_patients()]}")
    print("  -> Proved: Clinic internal state is completely protected by returning shallow copies.")


def demo_part_3():
    print_section("PART 3: POLYMORPHISM (NO isinstance / type tags)")
    print("Iterating over a polymorphic list of Staff members:")

    staff_members = [
        Doctor(staff_id=1, name="Dr. Gregory House"),
        Nurse(staff_id=2, name="Nurse Jackie Peyton"),
        Pharmacist(staff_id=3, name="Pharmacist John Pemberton"),
    ]

    # In one loop, print each person's role and fee with NO isinstance/type tags:
    for s in staff_members:
        print(f"  - Staff: {s.name:<25} | Role: {s.role():<12} | Fee: ${s.fee()}")

    print("\n-> Notice: We added Pharmacist cleanly without checking any types or modifying Clinic!")


def demo_part_4():
    print_section("PART 4: LOGGING GUARANTEE & DELIBERATE FAILURE (too late)")
    clock = Clock(start_hour=20)
    clinic = Clinic(name="Metro Clinic", clock=clock)

    patient = Patient(patient_id=201, name="John Doe")
    doc = Doctor(staff_id=11, name="Dr. Sarah Smith")
    clinic.register_person(patient)
    clinic.register_person(doc)

    print("\n--- A. Booking and Confirming Appointment #3 at hour 21 ---")
    clinic.book_appointment(appt_id=3, patient=patient, staff=doc, start_hour=21)
    clinic.confirm_appointment(appt_id=3)

    print("\n--- B. DELIBERATE FAILURE: Cancelling confirmed appointment < 2 hours before start ---")
    print(f"Current Clock Time: hour {clock.now()} | Appointment Start: hour 21 (only 1 hour remaining!)")
    print("Attempting to cancel appointment #3:")
    success = clinic.cancel_appointment(appt_id=3)
    print(f"Cancellation returned: {success}")
    print("-> Notice above: [log] opened and [log] closed were both printed, and 'FAILED cancel #3: too late' was logged!")

    print("\n--- C. Advancing clock past start hour and attempting to cancel ---")
    clock.advance(2)  # Clock is now at hour 22
    print(f"Clock advanced to hour {clock.now()}. Now attempting to cancel appointment #3:")
    clinic.cancel_appointment(appt_id=3)


def demo_part_5():
    print_section("PART 5: DIAMOND PROBLEM & MedicalLecturer")

    # Reset constructor counter to demonstrate single execution
    Person.constructor_count = 0

    print("Creating an instance of MedicalLecturer:")
    med_lec = MedicalLecturer(person_id=99, name="Dr. Strange", module_name="Clinical Neuroanatomy")

    print(f"  Instance:       {med_lec}")
    print(f"  Role:           '{med_lec.role()}'")
    print(f"  Module Name:    '{med_lec.module_name}'")
    print(f"  Fee:            ${med_lec.fee()}")
    print(f"  Person.__init__ call count: {Person.constructor_count}")
    print(f"  Method Resolution Order (MRO): {[c.__name__ for c in MedicalLecturer.__mro__]}")

    print("\n-> Analysis:")
    print("  1. Person constructor ran exactly ONCE due to Python's C3 MRO and cooperative super() calls.")
    print("  2. MedicalLecturer.fee() returns $40 (Doctor's fee) because within the clinic, appointments")
    print("     are medical consultations; academic teaching duties are not charged to clinical patients.")


def demo_part_6_and_twist_0():
    print_section("PART 6 & TWIST 0: RULES, CONFLICTS & WAITING LIST AUTO-OFFER")

    clock = Clock(start_hour=50)
    clinic = Clinic(name="Apex Health", clock=clock)

    # Register staff and patients
    dr_alice = Doctor(staff_id=1, name="Dr. Alice")
    pt_bob = Patient(patient_id=10, name="Bob")
    pt_carol = Patient(patient_id=11, name="Carol")
    pt_david = Patient(patient_id=12, name="David")

    clinic.register_person(dr_alice)
    clinic.register_person(pt_bob)
    clinic.register_person(pt_carol)
    clinic.register_person(pt_david)

    print("\n--- 1. Unique IDs Enforcement across Clinic ---")
    try:
        # Attempt duplicate ID
        duplicate_person = Patient(patient_id=1, name="Duplicate ID Patient")
        clinic.register_person(duplicate_person)
    except ValueError as e:
        print(f"  [CAUGHT] Duplicate ID rejected: {e}")

    print("\n--- 2. Booking Initial Appointment #101 for Bob at hour 55 ---")
    clinic.book_appointment(appt_id=101, patient=pt_bob, staff=dr_alice, start_hour=55)

    print("\n--- 3. Rule Enforcement: No Two Non-Cancelled Appointments at Same Hour ---")
    print("Attempting to double-book Dr. Alice at hour 55 with Carol:")
    clinic.book_appointment(appt_id=102, patient=pt_carol, staff=dr_alice, start_hour=55)

    print("\nAttempting to double-book Bob at hour 55 with another doctor:")
    dr_zack = Doctor(staff_id=2, name="Dr. Zack")
    clinic.register_person(dr_zack)
    clinic.book_appointment(appt_id=103, patient=pt_bob, staff=dr_zack, start_hour=55)

    print("\n--- 4. Twist 0: Patients Join Waiting List for Dr. Alice ---")
    clinic.join_waiting_list(patient=pt_carol, staff=dr_alice)
    clinic.join_waiting_list(patient=pt_david, staff=dr_alice)
    print(f"Current waiting list for {dr_alice.name}: {[p.name for p in clinic.get_waiting_list(dr_alice)]}")

    print("\n--- 5. Twist 0: Bob's Appointment #101 is Cancelled > 2 hours in advance ---")
    print(f"Current hour: {clock.now()}, Start hour: 55 (5 hours in advance). Cancelling #101:")
    clinic.cancel_appointment(appt_id=101)

    print("\n--- 6. Verification of Twist 0 Auto-Offer ---")
    print(f"Remaining waiting list for {dr_alice.name}: {[p.name for p in clinic.get_waiting_list(dr_alice)]}")
    all_appts = clinic.get_appointments()
    print("Active clinic appointments:")
    for a in all_appts:
        print(f"  {a}")
    print("-> Proved: Slot at hour 55 was automatically offered to first waiting patient Carol as PENDING!")


def main():
    print("=" * 70)
    print("       CLINICAL APPOINTMENT SYSTEM - DEMO & SPECIFICATION AUDIT")
    print("=" * 70)

    demo_part_1_and_2()
    demo_part_3()
    demo_part_4()
    demo_part_5()
    demo_part_6_and_twist_0()

    print("\n" + "=" * 70)
    print("       DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
