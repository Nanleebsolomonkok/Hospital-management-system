import requests
import time
base_url = 'http://localhost:5000'

def jget(r):
    try:
        return r.json()
    except Exception:
        return {'error': r.text[:200], 'status': r.status_code}

# 1. Login as Admin
s = requests.Session()
r = s.post(f"{base_url}/api/login", json={"username": "admin", "password": "password"})
print("Admin Login:", jget(r))

# 2. Get patients
r = s.get(f"{base_url}/api/patients")
data = jget(r)
patient_id = data.get('patients', [{}])[0].get('patient_id')
print("Patient ID:", patient_id)

# 3. Create Pharmacy Order
r = s.post(f"{base_url}/api/pharmacy/orders", json={
    "patient_id": patient_id,
    "item_id": 1,
    "quantity": 2
})
print("Create Pharmacy Order:", jget(r))

# 4. Get Pharmacy Orders
r = s.get(f"{base_url}/api/pharmacy/orders")
orders = jget(r).get('orders', [])
print("Pharmacy Orders:", orders)
order_id = orders[0]['order_id'] if orders else None

if order_id:
    # 5. Try dispensing unpaid order
    r = s.post(f"{base_url}/api/pharmacy/orders/{order_id}/dispense")
    print("Dispense Unpaid Order:", jget(r)) # Should fail

    # 6. Get billing
    r = s.get(f"{base_url}/api/billing")
    bills = jget(r).get('bills', [])
    print("Billing:", bills)
    bill = bills[0] if bills else None
    
    if bill:
        bill_id = bill['bill_id']
        amount = bill['total_amount']
        
        # 7. Pay bill
        r = s.post(f"{base_url}/api/billing/{bill_id}/pay", json={
            "payment_method": "Cash",
            "paid_amount": amount
        })
        print("Pay Bill:", jget(r))
        
        # 8. Try dispensing paid order
        r = s.post(f"{base_url}/api/pharmacy/orders/{order_id}/dispense")
        print("Dispense Paid Order:", jget(r)) # Should succeed

print("Done.")
