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
