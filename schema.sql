-- ============================================
-- MediCore Hospital Management System
-- Database Schema — schema.sql
-- ============================================

CREATE DATABASE IF NOT EXISTS HospitalManagement_STU001;
USE HospitalManagement_STU001;

-- ============================================
-- TABLES
-- ============================================

CREATE TABLE Roles_STU001 (
    role_id    INT PRIMARY KEY AUTO_INCREMENT,
    role_code  VARCHAR(20)  UNIQUE NOT NULL,
    role_name  VARCHAR(50)  NOT NULL,
    permissions TEXT,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Users_STU001 (
    user_id              INT PRIMARY KEY AUTO_INCREMENT,
    username             VARCHAR(50)  UNIQUE NOT NULL,
    password_hash        VARCHAR(64)  NOT NULL,
    password_changed_at  TIMESTAMP    NULL,
    must_change_password BOOLEAN      DEFAULT FALSE,
    email                VARCHAR(100),
    full_name            VARCHAR(100) NOT NULL,
    role                 VARCHAR(20)  NOT NULL,
    is_active            BOOLEAN      DEFAULT TRUE,
    last_login           TIMESTAMP    NULL,
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Departments_STU001 (
    department_id   INT PRIMARY KEY AUTO_INCREMENT,
    department_name VARCHAR(100) NOT NULL,
    location        VARCHAR(100),
    head_doctor_id  INT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Doctors_STU001 (
    doctor_id      INT PRIMARY KEY AUTO_INCREMENT,
    first_name     VARCHAR(50)  NOT NULL,
    last_name      VARCHAR(50)  NOT NULL,
    email          VARCHAR(100) UNIQUE NOT NULL,
    phone          VARCHAR(20),
    specialization VARCHAR(100),
    department_id  INT,
    salary         DECIMAL(10,2),
    hire_date      DATE,
    status         ENUM('Active','On Leave','Terminated') DEFAULT 'Active',
    FOREIGN KEY (department_id) REFERENCES Departments_STU001(department_id)
);

ALTER TABLE Departments_STU001
ADD CONSTRAINT fk_head_doctor_STU001
FOREIGN KEY (head_doctor_id) REFERENCES Doctors_STU001(doctor_id);

CREATE TABLE Patients_STU001 (
    patient_id              INT PRIMARY KEY AUTO_INCREMENT,
    first_name              VARCHAR(50) NOT NULL,
    last_name               VARCHAR(50) NOT NULL,
    date_of_birth           DATE        NOT NULL,
    gender                  ENUM('Male','Female','Other') NOT NULL,
    email                   VARCHAR(100),
    phone                   VARCHAR(20),
    address                 TEXT,
    blood_group             VARCHAR(5),
    emergency_contact_name  VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    insurance_id            VARCHAR(50),
    registration_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Appointments_STU001 (
    appointment_id   INT PRIMARY KEY AUTO_INCREMENT,
    patient_id       INT  NOT NULL,
    doctor_id        INT  NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status           ENUM('Scheduled','Completed','Cancelled','No Show') DEFAULT 'Scheduled',
    reason           TEXT,
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES Patients_STU001(patient_id),
    FOREIGN KEY (doctor_id)  REFERENCES Doctors_STU001(doctor_id)
);

CREATE TABLE MedicalRecords_STU001 (
    record_id      INT PRIMARY KEY AUTO_INCREMENT,
    patient_id     INT  NOT NULL,
    doctor_id      INT  NOT NULL,
    appointment_id INT,
    diagnosis      TEXT NOT NULL,
    prescription   TEXT,
    treatment_plan TEXT,
    lab_results    TEXT,
    record_date    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id)     REFERENCES Patients_STU001(patient_id),
    FOREIGN KEY (doctor_id)      REFERENCES Doctors_STU001(doctor_id),
    FOREIGN KEY (appointment_id) REFERENCES Appointments_STU001(appointment_id)
);

CREATE TABLE Billing_STU001 (
    bill_id        INT PRIMARY KEY AUTO_INCREMENT,
    patient_id     INT            NOT NULL,
    appointment_id INT,
    amount         DECIMAL(10,2)  NOT NULL,
    tax_amount     DECIMAL(10,2)  DEFAULT 0.00,
    total_amount   DECIMAL(10,2)  NOT NULL,
    payment_status ENUM('Pending','Paid','Overdue','Cancelled') DEFAULT 'Pending',
    payment_method VARCHAR(50),
    billing_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id)     REFERENCES Patients_STU001(patient_id),
    FOREIGN KEY (appointment_id) REFERENCES Appointments_STU001(appointment_id)
);

CREATE TABLE AuditLog_STU001 (
    log_id           INT PRIMARY KEY AUTO_INCREMENT,
    table_name       VARCHAR(50),
    action           VARCHAR(30),
    record_id        INT,
    old_values       TEXT,
    new_values       TEXT,
    user_name        VARCHAR(100),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address       VARCHAR(50)
);

-- ============================================
-- FUNCTION: Calculate patient age
-- ============================================

DELIMITER //

CREATE FUNCTION CalculateAge_STU001(p_dob DATE)
RETURNS INT
DETERMINISTIC
NO SQL
BEGIN
    RETURN TIMESTAMPDIFF(YEAR, p_dob, CURDATE());
END //

-- ============================================
-- FUNCTION: Check doctor availability
-- ============================================

CREATE FUNCTION IsDoctorAvailable_STU001(
    p_doctor_id INT,
    p_date      DATE,
    p_time      TIME
)
RETURNS BOOLEAN
READS SQL DATA
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count
    FROM Appointments_STU001
    WHERE doctor_id       = p_doctor_id
      AND appointment_date = p_date
      AND appointment_time = p_time
      AND status          != 'Cancelled';
    RETURN v_count = 0;
END //

-- ============================================
-- PROCEDURE: Register patient
-- ============================================

CREATE PROCEDURE RegisterPatient_STU001(
    IN  p_first_name      VARCHAR(50),
    IN  p_last_name       VARCHAR(50),
    IN  p_dob             DATE,
    IN  p_gender          ENUM('Male','Female','Other'),
    IN  p_email           VARCHAR(100),
    IN  p_phone           VARCHAR(20),
    IN  p_address         TEXT,
    IN  p_blood_group     VARCHAR(5),
    IN  p_emergency_name  VARCHAR(100),
    IN  p_emergency_phone VARCHAR(20),
    IN  p_insurance_id    VARCHAR(50),
    OUT p_patient_id      INT,
    OUT p_status_message  VARCHAR(100)
)
BEGIN
    DECLARE v_email_exists INT DEFAULT 0;

    IF p_email IS NOT NULL AND p_email != '' THEN
        SELECT COUNT(*) INTO v_email_exists
        FROM Patients_STU001
        WHERE email = p_email;
    END IF;

    IF v_email_exists > 0 THEN
        SET p_patient_id     = -1;
        SET p_status_message = 'Error: Email address already registered';
    ELSE
        INSERT INTO Patients_STU001 (
            first_name, last_name, date_of_birth, gender, email,
            phone, address, blood_group, emergency_contact_name,
            emergency_contact_phone, insurance_id
        ) VALUES (
            p_first_name, p_last_name, p_dob, p_gender, p_email,
            p_phone, p_address, p_blood_group, p_emergency_name,
            p_emergency_phone, p_insurance_id
        );
        SET p_patient_id     = LAST_INSERT_ID();
        SET p_status_message = 'Patient registered successfully';
    END IF;
END //

-- ============================================
-- PROCEDURE: Schedule appointment
-- ============================================

CREATE PROCEDURE ScheduleAppointment_STU001(
    IN  p_patient_id       INT,
    IN  p_doctor_id        INT,
    IN  p_appointment_date DATE,
    IN  p_appointment_time TIME,
    IN  p_reason           TEXT,
    OUT p_appointment_id   INT,
    OUT p_status_message   VARCHAR(100)
)
BEGIN
    DECLARE v_patient_exists   INT DEFAULT 0;
    DECLARE v_doctor_active    INT DEFAULT 0;
    DECLARE v_slot_taken       INT DEFAULT 0;

    SELECT COUNT(*) INTO v_patient_exists
    FROM Patients_STU001 WHERE patient_id = p_patient_id;

    SELECT COUNT(*) INTO v_doctor_active
    FROM Doctors_STU001 WHERE doctor_id = p_doctor_id AND status = 'Active';

    SELECT COUNT(*) INTO v_slot_taken
    FROM Appointments_STU001
    WHERE doctor_id        = p_doctor_id
      AND appointment_date = p_appointment_date
      AND appointment_time = p_appointment_time
      AND status          != 'Cancelled';

    IF v_patient_exists = 0 THEN
        SET p_appointment_id  = -1;
        SET p_status_message  = 'Error: Patient not found';
    ELSEIF v_doctor_active = 0 THEN
        SET p_appointment_id  = -1;
        SET p_status_message  = 'Error: Doctor not found or not currently active';
    ELSEIF v_slot_taken > 0 THEN
        SET p_appointment_id  = -1;
        SET p_status_message  = 'Error: That time slot is already booked';
    ELSE
        INSERT INTO Appointments_STU001
            (patient_id, doctor_id, appointment_date, appointment_time, reason)
        VALUES
            (p_patient_id, p_doctor_id, p_appointment_date, p_appointment_time, p_reason);

        SET p_appointment_id  = LAST_INSERT_ID();
        SET p_status_message  = 'Appointment scheduled successfully';
    END IF;
END //

-- ============================================
-- PROCEDURE: Process payment
-- ============================================

CREATE PROCEDURE ProcessPayment_STU001(
    IN  p_bill_id        INT,
    IN  p_payment_method VARCHAR(50),
    IN  p_paid_amount    DECIMAL(10,2),
    OUT p_status_message VARCHAR(100)
)
BEGIN
    DECLARE v_total  DECIMAL(10,2);
    DECLARE v_status VARCHAR(20);

    SELECT total_amount, payment_status
    INTO   v_total, v_status
    FROM   Billing_STU001
    WHERE  bill_id = p_bill_id;

    IF v_status IS NULL THEN
        SET p_status_message = 'Error: Bill not found';
    ELSEIF v_status = 'Paid' THEN
        SET p_status_message = 'Error: Bill has already been paid';
    ELSEIF v_status = 'Cancelled' THEN
        SET p_status_message = 'Error: Bill has been cancelled';
    ELSEIF p_paid_amount < v_total THEN
        SET p_status_message = 'Error: Paid amount is less than total due';
    ELSE
        UPDATE Billing_STU001
        SET    payment_status = 'Paid',
               payment_method = p_payment_method
        WHERE  bill_id = p_bill_id;

        SET p_status_message = 'Payment processed successfully';
    END IF;
END //

-- ============================================
-- PROCEDURE: Wellness eligibility check
-- ============================================

CREATE PROCEDURE CheckWellnessEligibility_STU001(
    IN  p_patient_id       INT,
    OUT p_eligibility_status VARCHAR(60),
    OUT p_discount_percent   DECIMAL(5,2)
)
BEGIN
    DECLARE v_age            INT;
    DECLARE v_visit_count    INT DEFAULT 0;
    DECLARE v_last_visit     DATE;
    DECLARE v_has_chronic    BOOLEAN DEFAULT FALSE;

    SELECT CalculateAge_STU001(date_of_birth) INTO v_age
    FROM   Patients_STU001 WHERE patient_id = p_patient_id;

    SELECT COUNT(*), MAX(appointment_date)
    INTO   v_visit_count, v_last_visit
    FROM   Appointments_STU001
    WHERE  patient_id = p_patient_id AND status = 'Completed';

    SELECT EXISTS (
        SELECT 1 FROM MedicalRecords_STU001
        WHERE  patient_id = p_patient_id
          AND (diagnosis LIKE '%diabetes%' OR diagnosis LIKE '%hypertension%')
    ) INTO v_has_chronic;

    IF v_age IS NULL THEN
        SET p_eligibility_status = 'Error: Patient not found';
        SET p_discount_percent   = 0.00;
    ELSEIF v_age >= 65 THEN
        SET p_eligibility_status = 'Eligible — Senior Citizen Program';
        SET p_discount_percent   = 25.00;
    ELSEIF v_has_chronic AND v_visit_count >= 3 THEN
        SET p_eligibility_status = 'Eligible — Chronic Care Program';
        SET p_discount_percent   = 20.00;
    ELSEIF v_visit_count >= 5 THEN
        SET p_eligibility_status = 'Eligible — Loyalty Program';
        SET p_discount_percent   = 15.00;
    ELSEIF v_age <= 18 AND v_visit_count >= 2 THEN
        SET p_eligibility_status = 'Eligible — Pediatric Wellness';
        SET p_discount_percent   = 10.00;
    ELSEIF v_last_visit IS NOT NULL AND DATEDIFF(CURDATE(), v_last_visit) > 365 THEN
        SET p_eligibility_status = 'Eligible — Return Patient Offer';
        SET p_discount_percent   = 30.00;
    ELSE
        SET p_eligibility_status = 'Not Eligible — Standard Rates Apply';
        SET p_discount_percent   = 0.00;
    END IF;

    -- Cap discount at 30 %
    IF p_discount_percent > 30.00 THEN
        SET p_discount_percent = 30.00;
    END IF;
END //

-- ============================================
-- TRIGGERS
-- ============================================

-- 1. Audit patient updates
CREATE TRIGGER trg_patient_audit_STU001
AFTER UPDATE ON Patients_STU001
FOR EACH ROW
BEGIN
    INSERT INTO AuditLog_STU001 (table_name, action, record_id, old_values, new_values, user_name)
    VALUES (
        'Patients_STU001', 'UPDATE', OLD.patient_id,
        CONCAT('Name:', OLD.first_name, ' ', OLD.last_name, ', Phone:', OLD.phone),
        CONCAT('Name:', NEW.first_name, ' ', NEW.last_name, ', Phone:', NEW.phone),
        CURRENT_USER()
    );
END //

-- 2. Validate appointment before insert
CREATE TRIGGER trg_validate_appointment_STU001
BEFORE INSERT ON Appointments_STU001
FOR EACH ROW
BEGIN
    DECLARE v_doctor_status VARCHAR(20);
    SELECT status INTO v_doctor_status FROM Doctors_STU001 WHERE doctor_id = NEW.doctor_id;

    IF v_doctor_status != 'Active' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot schedule appointment with an inactive doctor';
    END IF;

    IF NEW.appointment_date < CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot schedule an appointment in the past';
    END IF;
END //

-- 3. Audit new medical records
CREATE TRIGGER trg_after_medical_record_STU001
AFTER INSERT ON MedicalRecords_STU001
FOR EACH ROW
BEGIN
    INSERT INTO AuditLog_STU001 (table_name, action, record_id, old_values, new_values, user_name)
    VALUES (
        'MedicalRecords_STU001', 'INSERT', NEW.record_id, NULL,
        CONCAT('Patient:', NEW.patient_id, ', Doctor:', NEW.doctor_id,
               ', Dx:', LEFT(NEW.diagnosis, 50)),
        CURRENT_USER()
    );
END //

-- 4. Mark appointment complete when billing is created
CREATE TRIGGER trg_after_billing_STU001
AFTER INSERT ON Billing_STU001
FOR EACH ROW
BEGIN
    IF NEW.appointment_id IS NOT NULL THEN
        UPDATE Appointments_STU001
        SET    status = 'Completed'
        WHERE  appointment_id = NEW.appointment_id;
    END IF;
END //

-- 5. Prevent deletion of paid bills
CREATE TRIGGER trg_prevent_bill_delete_STU001
BEFORE DELETE ON Billing_STU001
FOR EACH ROW
BEGIN
    IF OLD.payment_status = 'Paid' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot delete a paid bill — use cancellation instead';
    END IF;
END //

DELIMITER ;

-- ============================================
-- SAMPLE DATA
-- ============================================

INSERT INTO Roles_STU001 (role_code, role_name, permissions) VALUES
('ADMIN',        'System Administrator',    'ALL'),
('DOCTOR',       'Medical Doctor',          'PATIENT_VIEW,MEDICAL_RECORD_EDIT,APPOINTMENT_VIEW'),
('RECEPTIONIST', 'Front Desk Receptionist', 'PATIENT_EDIT,APPOINTMENT_EDIT'),
('BILLING',      'Billing Staff',           'BILLING_EDIT,PATIENT_VIEW_LIMITED'),
('GUEST',        'Guest User',              'PATIENT_VIEW_LIMITED');

-- Default password for all demo accounts: "password"
-- SHA-256 hash of "password"
INSERT INTO Users_STU001 (username, password_hash, email, full_name, role, is_active) VALUES
('admin',      '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'admin@hospital.com',     'System Administrator', 'ADMIN',        TRUE),
('doctor1',    '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'john.smith@hospital.com','Dr. John Smith',       'DOCTOR',       TRUE),
('reception1', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'jane@hospital.com',      'Jane Receptionist',    'RECEPTIONIST', TRUE),
('billing1',   '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'bob@hospital.com',       'Bob Accountant',       'BILLING',      TRUE);

INSERT INTO Departments_STU001 (department_name, location) VALUES
('Cardiology',   'Building A, Floor 2'),
('Neurology',    'Building A, Floor 3'),
('Pediatrics',   'Building B, Floor 1'),
('Orthopedics',  'Building B, Floor 2'),
('Emergency',    'Building C, Ground Floor');

INSERT INTO Doctors_STU001 (first_name, last_name, email, phone, specialization, department_id, salary, hire_date, status) VALUES
('John',    'Smith',   'john.smith@hospital.com',    '555-0101', 'Cardiologist',       1, 150000.00, '2020-01-15', 'Active'),
('Sarah',   'Johnson', 'sarah.johnson@hospital.com', '555-0102', 'Neurologist',        2, 160000.00, '2019-06-20', 'Active'),
('Michael', 'Brown',   'michael.brown@hospital.com', '555-0103', 'Pediatrician',       3, 120000.00, '2021-03-10', 'Active'),
('Emily',   'Davis',   'emily.davis@hospital.com',   '555-0104', 'Orthopedic Surgeon', 4, 155000.00, '2018-11-05', 'Active'),
('David',   'Wilson',  'david.wilson@hospital.com',  '555-0105', 'Emergency Physician',5, 140000.00, '2020-08-12', 'Active');

UPDATE Departments_STU001 SET head_doctor_id = 1 WHERE department_id = 1;
UPDATE Departments_STU001 SET head_doctor_id = 2 WHERE department_id = 2;

INSERT INTO Patients_STU001 (first_name, last_name, date_of_birth, gender, email, phone, address, blood_group, emergency_contact_name, emergency_contact_phone, insurance_id) VALUES
('Alice',    'Anderson', '1985-05-15', 'Female', 'alice@email.com',    '555-1001', '123 Main St, City',  'A+',  'Bob Anderson',   '555-1002', 'INS001'),
('Robert',   'Taylor',   '1978-12-20', 'Male',   'robert@email.com',   '555-1003', '456 Oak Ave, City',  'O-',  'Mary Taylor',    '555-1004', 'INS002'),
('Jennifer', 'Martinez', '1990-07-08', 'Female', 'jennifer@email.com', '555-1005', '789 Pine Rd, City',  'B+',  'Carlos Martinez','555-1006', 'INS003'),
('James',    'Wilson',   '1965-03-25', 'Male',   'james@email.com',    '555-1007', '321 Elm St, City',   'AB+', 'Linda Wilson',   '555-1008', 'INS004'),
('Patricia', 'Garcia',   '1995-11-12', 'Female', 'patricia@email.com', '555-1009', '654 Maple Dr, City', 'A-',  'Jose Garcia',    '555-1010', 'INS005');

INSERT INTO Appointments_STU001 (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES
(1, 1, CURDATE() + INTERVAL 1 DAY, '09:00:00', 'Scheduled', 'Annual heart checkup'),
(2, 2, CURDATE() + INTERVAL 1 DAY, '10:30:00', 'Scheduled', 'Migraine consultation'),
(3, 3, CURDATE() + INTERVAL 2 DAY, '14:00:00', 'Scheduled', 'Child vaccination'),
(4, 4, CURDATE() + INTERVAL 2 DAY, '11:00:00', 'Scheduled', 'Knee pain evaluation'),
(5, 5, CURDATE() + INTERVAL 1 DAY, '16:00:00', 'Scheduled', 'Emergency follow-up');

INSERT INTO MedicalRecords_STU001 (patient_id, doctor_id, appointment_id, diagnosis, prescription, treatment_plan) VALUES
(1, 1, 1, 'Mild hypertension',       'Lisinopril 10mg daily',            'Diet modification, exercise, follow-up in 3 months'),
(2, 2, 2, 'Chronic migraine',        'Sumatriptan 50mg as needed',       'Avoid triggers, stress management, neurology follow-up'),
(3, 3, 3, 'Routine checkup',         'MMR vaccine administered',          'Continue regular vaccinations per schedule'),
(4, 4, 4, 'Osteoarthritis right knee','Ibuprofen 400mg TID + physio',    'Knee strengthening exercises, weight management'),
(5, 5, 5, 'Acute bronchitis',        'Azithromycin 500mg daily × 5 days','Rest, hydration, return if symptoms worsen');

INSERT INTO Billing_STU001 (patient_id, appointment_id, amount, tax_amount, total_amount, payment_status, payment_method) VALUES
(1, 1, 200.00, 20.00, 220.00, 'Paid',    'Credit Card'),
(2, 2, 250.00, 25.00, 275.00, 'Pending', NULL),
(3, 3, 150.00, 15.00, 165.00, 'Paid',    'Insurance'),
(4, 4, 300.00, 30.00, 330.00, 'Pending', NULL),
(5, 5, 180.00, 18.00, 198.00, 'Overdue', NULL);

-- ============================================
-- DATABASE-LEVEL ROLES (MySQL 8+)
-- ============================================

CREATE ROLE IF NOT EXISTS 'medical_staff_STU001';
CREATE ROLE IF NOT EXISTS 'admin_staff_STU001';
CREATE ROLE IF NOT EXISTS 'finance_staff_STU001';
CREATE ROLE IF NOT EXISTS 'read_only_STU001';

-- Medical staff
GRANT SELECT, INSERT, UPDATE ON HospitalManagement_STU001.MedicalRecords_STU001 TO 'medical_staff_STU001';
GRANT SELECT ON HospitalManagement_STU001.Patients_STU001                        TO 'medical_staff_STU001';
GRANT SELECT, UPDATE ON HospitalManagement_STU001.Appointments_STU001            TO 'medical_staff_STU001';
GRANT SELECT (doctor_id, first_name, last_name, specialization, department_id)
    ON HospitalManagement_STU001.Doctors_STU001                                  TO 'medical_staff_STU001';

-- Admin staff
GRANT SELECT, INSERT, UPDATE ON HospitalManagement_STU001.Patients_STU001        TO 'admin_staff_STU001';
GRANT SELECT, INSERT, UPDATE, DELETE ON HospitalManagement_STU001.Appointments_STU001 TO 'admin_staff_STU001';
GRANT SELECT (doctor_id, first_name, last_name, specialization, department_id, status)
    ON HospitalManagement_STU001.Doctors_STU001                                  TO 'admin_staff_STU001';

-- Finance staff
GRANT ALL PRIVILEGES ON HospitalManagement_STU001.Billing_STU001                 TO 'finance_staff_STU001';
GRANT SELECT (patient_id, first_name, last_name, email, phone, insurance_id)
    ON HospitalManagement_STU001.Patients_STU001                                 TO 'finance_staff_STU001';

-- Read-only
GRANT SELECT ON HospitalManagement_STU001.Departments_STU001                     TO 'read_only_STU001';
GRANT SELECT (patient_id, first_name, last_name, gender, registration_date)
    ON HospitalManagement_STU001.Patients_STU001                                 TO 'read_only_STU001';
GRANT SELECT ON HospitalManagement_STU001.Doctors_STU001                         TO 'read_only_STU001';
USE HospitalManagement_STU001;

-- ============================================
-- PHARMACY MODULE
-- ============================================
CREATE TABLE IF NOT EXISTS Pharmacy_Inventory_STU001 (
    item_id        INT PRIMARY KEY AUTO_INCREMENT,
    item_name      VARCHAR(100) NOT NULL,
    category       VARCHAR(50),
    stock_quantity INT DEFAULT 0,
    unit_price     DECIMAL(10,2) NOT NULL,
    expiry_date    DATE,
    supplier       VARCHAR(100),
    last_updated   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO Pharmacy_Inventory_STU001 (item_name, category, stock_quantity, unit_price, expiry_date) VALUES 
('Amoxicillin 500mg', 'Antibiotic', 500, 15.00, '2027-12-31'),
('Ibuprofen 400mg', 'Painkiller', 1000, 8.50, '2028-06-15'),
('Lisinopril 10mg', 'Blood Pressure', 300, 22.00, '2026-11-20'),
('Metformin 500mg', 'Diabetes', 450, 12.00, '2027-01-10');

-- ============================================
-- WARD & BED MODULE
-- ============================================
CREATE TABLE IF NOT EXISTS Wards_STU001 (
    ward_id      INT PRIMARY KEY AUTO_INCREMENT,
    ward_name    VARCHAR(50) NOT NULL,
    ward_type    ENUM('General', 'ICU', 'Maternity', 'Pediatric', 'Emergency') NOT NULL,
    capacity     INT NOT NULL
);

INSERT INTO Wards_STU001 (ward_name, ward_type, capacity) VALUES 
('North Wing General', 'General', 20),
('Intensive Care Unit A', 'ICU', 8),
('East Wing Maternity', 'Maternity', 12);

CREATE TABLE IF NOT EXISTS Beds_STU001 (
    bed_id       INT PRIMARY KEY AUTO_INCREMENT,
    ward_id      INT NOT NULL,
    bed_number   VARCHAR(20) NOT NULL,
    status       ENUM('Available', 'Occupied', 'Maintenance') DEFAULT 'Available',
    FOREIGN KEY (ward_id) REFERENCES Wards_STU001(ward_id)
);

INSERT INTO Beds_STU001 (ward_id, bed_number, status) VALUES 
(1, 'G-101', 'Available'), (1, 'G-102', 'Available'), (1, 'G-103', 'Available'),
(2, 'ICU-01', 'Available'), (2, 'ICU-02', 'Available'),
(3, 'M-201', 'Available'), (3, 'M-202', 'Available');

CREATE TABLE IF NOT EXISTS Admissions_STU001 (
    admission_id   INT PRIMARY KEY AUTO_INCREMENT,
    patient_id     INT NOT NULL,
    bed_id         INT NOT NULL,
    doctor_id      INT NOT NULL,
    admission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    discharge_date DATETIME NULL,
    status         ENUM('Admitted', 'Discharged') DEFAULT 'Admitted',
    reason         TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patients_STU001(patient_id),
    FOREIGN KEY (bed_id) REFERENCES Beds_STU001(bed_id),
    FOREIGN KEY (doctor_id) REFERENCES Doctors_STU001(doctor_id)
);

-- ============================================
-- LABORATORY MODULE
-- ============================================
CREATE TABLE IF NOT EXISTS Lab_Tests_STU001 (
    test_id      INT PRIMARY KEY AUTO_INCREMENT,
    test_name    VARCHAR(100) NOT NULL,
    test_type    VARCHAR(50),
    cost         DECIMAL(10,2) NOT NULL
);

INSERT INTO Lab_Tests_STU001 (test_name, test_type, cost) VALUES 
('Complete Blood Count (CBC)', 'Blood', 45.00),
('Lipid Panel', 'Blood', 60.00),
('Chest X-Ray', 'Radiology', 120.00),
('Urinalysis', 'Urine', 30.00);

CREATE TABLE IF NOT EXISTS Lab_Results_STU001 (
    result_id      INT PRIMARY KEY AUTO_INCREMENT,
    patient_id     INT NOT NULL,
    doctor_id      INT NOT NULL,
    test_id        INT NOT NULL,
    order_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result_date    TIMESTAMP NULL,
    status         ENUM('Pending', 'Completed', 'Cancelled') DEFAULT 'Pending',
    result_data    TEXT,
    remarks        TEXT,
    FOREIGN KEY (patient_id) REFERENCES Patients_STU001(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES Doctors_STU001(doctor_id),
    FOREIGN KEY (test_id) REFERENCES Lab_Tests_STU001(test_id)
);
