USE HospitalManagement_STU001;

CREATE TABLE IF NOT EXISTS Pharmacy_Orders_STU001 (
    order_id       INT PRIMARY KEY AUTO_INCREMENT,
    patient_id     INT NOT NULL,
    item_id        INT NOT NULL,
    quantity       INT DEFAULT 1,
    bill_id        INT,
    status         ENUM('Pending Payment', 'Paid', 'Dispensed') DEFAULT 'Pending Payment',
    order_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES Patients_STU001(patient_id),
    FOREIGN KEY (item_id) REFERENCES Pharmacy_Inventory_STU001(item_id),
    FOREIGN KEY (bill_id) REFERENCES Billing_STU001(bill_id)
);

-- Note: We add bill_id to Lab_Results to track payment
ALTER TABLE Lab_Results_STU001 ADD COLUMN bill_id INT NULL;
ALTER TABLE Lab_Results_STU001 ADD CONSTRAINT fk_lab_bill FOREIGN KEY (bill_id) REFERENCES Billing_STU001(bill_id);

-- Modify Billing to describe what the bill is for (Optional but helpful)
ALTER TABLE Billing_STU001 ADD COLUMN bill_type VARCHAR(50) DEFAULT 'General';
