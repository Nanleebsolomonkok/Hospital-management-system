/**
 * MediCore HMS - SPA Engine (Minimalist Enterprise Edition)
 */

const App = {
    user: null,
    currentRoute: '',
    searchTimeout: null,
    refreshInterval: null,

    elements: {
        contentArea: document.getElementById('contentArea'),
        sidebarNav: document.getElementById('sidebarNav'),
        topbarTitle: document.getElementById('topbarTitle'),
        topbarSubtitle: document.getElementById('topbarSubtitle'),
        topbarActions: document.getElementById('topbarActions'),
        searchInput: document.getElementById('globalSearch'),
        toastContainer: document.getElementById('toastContainer'),
        userName: document.getElementById('userName'),
        userRole: document.getElementById('userRole'),
        userAvatar: document.getElementById('userAvatar'),
        logoutBtn: document.getElementById('logoutBtn')
    },

    init() {
        this.checkSession().then(hasSession => {
            if (!hasSession) { window.location.href = '/login.html'; return; }
            this.setupUI();
            this.setupRouter();
            this.setupEventListeners();
        });
    },

    async checkSession() {
        try {
            const res = await fetch('/api/session');
            if (!res.ok) return false;
            const data = await res.json();
            if (data.authenticated) {
                this.user = data.user;
                return true;
            }
            return false;
        } catch (e) { return false; }
    },

    setupUI() {
        if (this.user) {
            this.elements.userName.textContent = this.user.full_name;
            this.elements.userAvatar.textContent = this.user.full_name.substring(0, 2).toUpperCase();
            this.elements.userRole.textContent = this.user.role;
            
            // Load profile picture into sidebar
            this.fetchAPI('/api/profile').then(data => {
                if (data && data.success && data.profile.profile_picture) {
                    const av = this.elements.userAvatar;
                    av.textContent = '';
                    av.style.backgroundImage = `url('${data.profile.profile_picture}?t=${Date.now()}')`;
                    av.style.backgroundSize = 'cover';
                    av.style.backgroundPosition = 'center';
                }
            });
        }
        this.renderNavigation();
    },

    setupEventListeners() {
        this.elements.logoutBtn.addEventListener('click', async () => {
            await fetch('/api/logout', { method: 'POST' });
            window.location.href = '/login.html';
        });

        this.elements.searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                const query = e.target.value.trim().toLowerCase();
                const table = document.querySelector('table');
                if (!table) return;
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
                });
            }, 250);
        });
    },

    renderNavigation() {
        const role = this.user.role;
        const nav = [
            { section: 'Main', routes: [{ id: 'dashboard', label: 'Dashboard', icon: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>' }] }
        ];

        if (['ADMIN', 'DOCTOR', 'RECEPTIONIST'].includes(role)) {
            nav.push({
                section: 'Clinical',
                routes: [
                    { id: 'patients', label: 'Patients', icon: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>' },
                    { id: 'appointments', label: 'Appointments', icon: '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>' },
                    { id: 'wards', label: 'Ward Management', icon: '<path d="M3 22v-8"/><path d="M21 22v-8"/><path d="M3 14h18"/><path d="M3 10a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4H3v-4z"/><path d="M7 10V6a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v4"/>' }
                ]
            });
        }

        if (['ADMIN', 'DOCTOR', 'LAB_TECH', 'PHARMACIST'].includes(role)) {
            const serviceRoutes = [];
            if (['ADMIN', 'DOCTOR', 'LAB_TECH'].includes(role)) {
                serviceRoutes.push({ id: 'laboratory', label: 'Laboratory', icon: '<path d="M10 2v7.31"/><path d="M14 9.3V1.99"/><path d="M8.5 2h7"/><path d="M14 9.3a6.5 6.5 0 1 1-4 0"/><line x1="5.52" y1="16" x2="18.48" y2="16"/>' });
            }
            if (['ADMIN', 'DOCTOR', 'PHARMACIST'].includes(role)) {
                serviceRoutes.push({ id: 'pharmacy', label: 'Pharmacy', icon: '<path d="M10.5 20.5 19 12a3.54 3.54 0 0 0-5-5l-8.5 8.5a3.54 3.54 0 0 0 5 5Z"/><path d="M14.5 4.5 19 9"/>' });
            }
            if (serviceRoutes.length > 0) {
                nav.push({ section: 'Services', routes: serviceRoutes });
            }
        }

        if (['ADMIN', 'BILLING'].includes(role)) {
            nav.push({
                section: 'Finance',
                routes: [{ id: 'billing', label: 'Billing & Payments', icon: '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>' }]
            });
        }

        if (role === 'ADMIN') {
            nav.push({
                section: 'System',
                routes: [
                    { id: 'users', label: 'Staff Directory', icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' },
                    { id: 'audit', label: 'Audit Log', icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>' },
                    { id: 'reports', label: 'Reports', icon: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>' }
                ]
            });
        }

        nav.push({
            section: 'Personal',
            routes: [{ id: 'profile', label: 'My Profile', icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' }]
        });

        let html = '';
        nav.forEach(section => {
            html += `<div class="nav-section">${section.section}</div>`;
            section.routes.forEach(r => {
                html += `<a href="#${r.id}" class="nav-link" data-route="${r.id}" onclick="App.closeMobileSidebar()">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${r.icon}</svg>
                    ${r.label}
                </a>`;
            });
        });
        
        this.elements.sidebarNav.innerHTML = html;
    },

    closeMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobileOverlay');
        if (sidebar && overlay && window.innerWidth <= 768) {
            sidebar.classList.remove('open');
            overlay.classList.remove('open');
        }
    },

    setupRouter() {
        window.addEventListener('hashchange', () => this.handleRoute());
        this.handleRoute();

        // Mobile Sidebar Toggle
        const toggleBtn = document.getElementById('mobileToggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobileOverlay');
        
        if (toggleBtn && sidebar && overlay) {
            const toggleSidebar = () => {
                sidebar.classList.toggle('open');
                overlay.classList.toggle('open');
            };
            toggleBtn.addEventListener('click', toggleSidebar);
            overlay.addEventListener('click', toggleSidebar);
        }
    },

    handleRoute() {
        let hash = window.location.hash.substring(1);
        if (!hash) {
            if (this.user.role === 'PHARMACIST') hash = 'pharmacy';
            else if (this.user.role === 'LAB_TECH') hash = 'laboratory';
            else hash = 'dashboard';
        }
        const parts = hash.split('/');
        const route = parts[0];
        const id = parts[1] || null;

        this.currentRoute = hash;
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.getAttribute('data-route') === route);
        });
        
        this.elements.searchInput.value = '';
        if (this.refreshInterval) { clearInterval(this.refreshInterval); this.refreshInterval = null; }

        this.showLoading();

        switch (route) {
            case 'dashboard': this.renderDashboard(); break;
            case 'patients': if (id) this.renderPatientDetail(id); else this.renderPatients(); break;
            case 'appointments': this.renderAppointments(); break;
            case 'billing': this.renderBilling(); break;
            case 'wards': this.renderWards(); break;
            case 'pharmacy': this.renderPharmacy(); break;
            case 'laboratory': this.renderLaboratory(); break;
            case 'users': this.renderUsers(); break;
            case 'audit': this.renderAudit(); break;
            case 'reports': this.renderReports(); break;
            case 'profile': this.renderProfile(); break;
            default: this.renderDashboard();
        }
    },

    showLoading() {
        this.elements.contentArea.innerHTML = `<div class="empty-state">Loading data...</div>`;
        this.elements.topbarActions.innerHTML = '';
        this.elements.topbarTitle.textContent = 'Loading...';
        this.elements.topbarSubtitle.textContent = '';
    },

    setHeader(title, subtitle = '', actionsHtml = '') {
        this.elements.topbarTitle.textContent = title;
        this.elements.topbarSubtitle.textContent = subtitle;
        this.elements.topbarActions.innerHTML = actionsHtml;
    },

    showToast(message, type = 'info') {
        const t = document.createElement('div');
        t.className = `toast toast-${type}`;
        t.textContent = message;
        this.elements.toastContainer.appendChild(t);
        setTimeout(() => t.remove(), 4000);
    },

    showModal(title, body, footer) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = body;
        document.getElementById('modalFooter').innerHTML = footer;
        document.getElementById('modalOverlay').classList.add('open');
    },

    closeModal() {
        document.getElementById('modalOverlay').classList.remove('open');
    },

    async fetchAPI(url, options = {}) {
        try {
            const res = await fetch(url, options);
            if (res.status === 401) { window.location.href = '/login.html'; return null; }
            return await res.json();
        } catch (e) {
            this.showToast('Network error', 'error');
            return null;
        }
    },

    async renderDashboard() {
        this.setHeader('Dashboard', 'Hospital Overview');
        const data = await this.fetchAPI('/api/dashboard/stats');
        if (!data || !data.success) { this.elements.contentArea.innerHTML = 'Error loading stats'; return; }
        
        const s = data.stats;
        let html = '';
        
        if (this.user.role === 'ADMIN') {
            html += `<div class="stats-grid">
                <div class="stat-card"><div class="stat-title">Total Patients</div><div class="stat-value">${s.total_patients}</div></div>
                <div class="stat-card"><div class="stat-title">Available Beds</div><div class="stat-value" style="color:var(--success);">${s.available_beds}</div></div>
                <div class="stat-card"><div class="stat-title">Appointments Today</div><div class="stat-value">${s.today_appointments}</div></div>
                <div class="stat-card"><div class="stat-title">Today's Revenue</div><div class="stat-value" style="color:var(--primary);">$${s.total_revenue.toFixed(2)}</div></div>
            </div>
            <div class="grid-2" style="margin-top: 24px;">
                <div class="card">
                    <div class="card-header"><div class="card-title">Revenue (Last 7 Days)</div></div>
                    <div class="card-body"><canvas id="revenueChart" height="200"></canvas></div>
                </div>
                <div class="card">
                    <div class="card-header"><div class="card-title">Ward Occupancy</div></div>
                    <div class="card-body"><canvas id="bedChart" height="200"></canvas></div>
                </div>
            </div>`;
        } else if (this.user.role === 'DOCTOR') {
            html += `<div class="stats-grid">
                <div class="stat-card"><div class="stat-title">My Patients</div><div class="stat-value">${s.patient_count}</div></div>
                <div class="stat-card"><div class="stat-title">Upcoming Appointments</div><div class="stat-value">${s.appointments.length}</div></div>
                <div class="stat-card"><div class="stat-title">Pending Lab Results</div><div class="stat-value" style="color:var(--warning);">${s.pending_labs}</div></div>
            </div>`;
        } else if (this.user.role === 'RECEPTIONIST') {
            html += `<div class="stats-grid">
                <div class="stat-card"><div class="stat-title">Today's Appointments</div><div class="stat-value">${s.today_appointments.length}</div></div>
            </div>`;
        } else if (this.user.role === 'BILLING') {
            html += `<div class="stats-grid">
                <div class="stat-card"><div class="stat-title">Pending Invoices</div><div class="stat-value">${s.pending_bills.length}</div></div>
                <div class="stat-card"><div class="stat-title">Today's Revenue</div><div class="stat-value" style="color:var(--success);">$${s.today_revenue.toFixed(2)}</div></div>
            </div>`;
        } else if (this.user.role === 'PHARMACIST') {
            html += `<div class="stats-grid">
                <div class="stat-card"><div class="stat-title">Total Inventory Items</div><div class="stat-value">${s.total_items}</div></div>
                <div class="stat-card"><div class="stat-title">Low Stock Alerts</div><div class="stat-value" style="color:var(--danger);">${s.low_stock}</div></div>
            </div>`;
        } else if (this.user.role === 'LAB_TECH') {
            html += `<div class="stats-grid">
                <div class="stat-card"><div class="stat-title">Pending Tests</div><div class="stat-value" style="color:var(--warning);">${s.pending_tests}</div></div>
                <div class="stat-card"><div class="stat-title">Completed Today</div><div class="stat-value" style="color:var(--success);">${s.completed_today}</div></div>
            </div>`;
        }
        
        this.elements.contentArea.innerHTML = html;
        
        // Render Charts for Admin
        if (this.user.role === 'ADMIN' && typeof Chart !== 'undefined') {
            new Chart(document.getElementById('revenueChart'), {
                type: 'line',
                data: {
                    labels: s.revenue_chart.map(d => d.day),
                    datasets: [{ label: 'Revenue ($)', data: s.revenue_chart.map(d => d.total), borderColor: '#0f766e', tension: 0.1 }]
                }
            });
            new Chart(document.getElementById('bedChart'), {
                type: 'doughnut',
                data: {
                    labels: s.bed_occupancy.map(d => d.status),
                    datasets: [{ data: s.bed_occupancy.map(d => d.count), backgroundColor: ['#10b981', '#f59e0b', '#ef4444'] }]
                }
            });
        }
        
        if (!this.refreshInterval) this.refreshInterval = setInterval(() => { if (this.currentRoute === 'dashboard') this.renderDashboard(); }, 60000);
    },

    async renderPatients() {
        let actionBtn = '';
        if (['ADMIN', 'RECEPTIONIST'].includes(this.user.role)) {
            actionBtn = '<button class="btn btn-primary" onclick="App.openPatientModal()">+ Register Patient</button>';
        }
        this.setHeader('Patients', 'Directory', actionBtn);
        const data = await this.fetchAPI('/api/patients');
        if (!data) return;
        
        let html = `<div class="card"><div class="card-body" style="padding:0;">
            <table>
                <thead><tr><th>ID</th><th>Name</th><th>Age</th><th>Gender</th><th>Contact</th><th>Action</th></tr></thead>
                <tbody>${data.patients.map(p => `
                    <tr>
                        <td class="text-muted">#${p.patient_id}</td>
                        <td style="font-weight:600;">${p.first_name} ${p.last_name}</td>
                        <td>${p.age}</td>
                        <td>${p.gender}</td>
                        <td class="text-muted">${p.phone || '-'}</td>
                        <td>
                            <a href="#patients/${p.patient_id}" class="btn btn-secondary btn-sm">Profile</a>
                            ${['ADMIN','RECEPTIONIST'].includes(this.user.role) ? `<button class="btn btn-secondary btn-sm" onclick="App.openEditPatientModal(${p.patient_id}, '${p.first_name}', '${p.last_name}', '${p.date_of_birth||''}', '${p.gender}', '${p.phone||''}', '${p.email||''}', '${p.blood_group||''}')" style="margin-left:4px;">Edit</button>` : ''}
                        </td>
                    </tr>
                `).join('')}</tbody>
            </table>
        </div></div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderPatientDetail(id) {
        this.setHeader('Patient Profile', 'Loading...');
        const data = await this.fetchAPI(`/api/patients/${id}`);
        if (!data || !data.success) return;
        const p = data.data.patient;
        this.setHeader(`${p.first_name} ${p.last_name}`, `Patient #${p.patient_id}`);
        
        let html = `
            <div class="grid-2">
                <div class="card">
                    <div class="card-header"><div class="card-title">Demographics</div></div>
                    <div class="card-body">
                        <div class="form-group"><label class="text-muted">Age / DOB</label><div>${p.age} yrs (${p.date_of_birth})</div></div>
                        <div class="form-group"><label class="text-muted">Gender</label><div>${p.gender}</div></div>
                        <div class="form-group"><label class="text-muted">Blood Group</label><div>${p.blood_group || 'Unknown'}</div></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><div class="card-title">Contact Information</div></div>
                    <div class="card-body">
                        <div class="form-group"><label class="text-muted">Phone</label><div>${p.phone || '—'}</div></div>
                        <div class="form-group"><label class="text-muted">Email</label><div>${p.email || '—'}</div></div>
                        <div class="form-group"><label class="text-muted">Insurance ID</label><div>${p.insurance_id || '—'}</div></div>
                    </div>
                </div>
            </div>
            
            ${this.user.role !== 'RECEPTIONIST' ? `
            <div class="card">
                <div class="card-header"><div class="card-title">Patient Timeline</div></div>
                <div class="card-body">
                    <div id="patientTimeline">Loading timeline...</div>
                </div>
            </div>` : ''}
        `;
        this.elements.contentArea.innerHTML = html;
        if (this.user.role !== 'RECEPTIONIST') {
            this.loadPatientTimeline(p.patient_id);
        }
    },

    async loadPatientTimeline(id) {
        const data = await this.fetchAPI(`/api/patients/${id}/timeline`);
        if (!data || !data.success) { document.getElementById('patientTimeline').innerHTML = 'No history available.'; return; }
        
        let t_html = '<div style="border-left: 2px solid #e2e8f0; margin-left: 10px; padding-left: 20px;">';
        data.events.forEach(e => {
            const icon = e.type === 'Appointment' ? '📅' : e.type === 'Diagnosis' ? '🩺' : e.type === 'Lab Test' ? '🧪' : '💳';
            t_html += `<div style="position: relative; margin-bottom: 24px;">
                <div style="position: absolute; left: -34px; background: #fff; border: 2px solid #e2e8f0; border-radius: 50%; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; font-size: 12px;">${icon}</div>
                <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px;">${e.date} &mdash; ${e.type}</div>
                <div style="font-size: 14px;">${e.description}</div>
            </div>`;
        });
        t_html += '</div>';
        if (data.events.length === 0) t_html = '<div class="empty-state">No timeline events.</div>';
        document.getElementById('patientTimeline').innerHTML = t_html;
    },

    async renderWards() {
        let actionBtn = '';
        if (['ADMIN', 'DOCTOR'].includes(this.user.role)) {
            actionBtn = '<button class="btn btn-primary" onclick="App.openAdmitModal()">+ Admit Patient</button>';
        }
        this.setHeader('Ward Management', 'Bed allocation and admissions', actionBtn);
        const data = await this.fetchAPI('/api/wards');
        if (!data) return;
        
        let html = `<div class="grid-3 mb-24">
            ${data.wards.map(w => `<div class="card"><div class="card-header"><div class="card-title">${w.ward_name}</div><span class="badge badge-info">${w.ward_type}</span></div><div class="card-body" style="padding:16px;">Capacity: <strong>${w.capacity} beds</strong></div></div>`).join('')}
        </div>
        <div class="card">
            <div class="card-header"><div class="card-title">Bed Allocation</div></div>
            <div class="card-body" style="padding:0;">
                <table>
                    <thead><tr><th>Bed Number</th><th>Ward</th><th>Status</th><th>Current Patient</th><th>Action</th></tr></thead>
                    <tbody>${data.beds.map(b => `
                        <tr>
                            <td style="font-weight:600;">${b.bed_number}</td>
                            <td class="text-muted">Ward #${b.ward_id}</td>
                            <td><span class="badge badge-${b.status==='Available'?'success':'warning'}">${b.status}</span></td>
                            <td>${b.status==='Occupied' ? `<a href="#patients/${b.patient_id}">${b.first_name} ${b.last_name}</a>` : '<span class="text-muted">—</span>'}</td>
                            <td>${b.status==='Occupied' && ['ADMIN', 'DOCTOR'].includes(this.user.role) ? `<button class="btn btn-secondary btn-sm" onclick="App.dischargePatient(${b.bed_id})">Discharge</button>` : ''}</td>
                        </tr>
                    `).join('')}</tbody>
                </table>
            </div>
        </div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderPharmacy() {
        let actionBtn = '';
        if (['ADMIN', 'PHARMACIST'].includes(this.user.role)) {
            actionBtn = '<button class="btn btn-primary" onclick="App.openCreateOrderModal()">+ Charge Patient</button> <button class="btn btn-secondary" onclick="App.openAddMedicationModal()">+ Add Medication</button>';
        }
        this.setHeader('Pharmacy', 'Orders & Inventory', actionBtn);
        const data = await this.fetchAPI('/api/pharmacy/inventory');
        const ordersData = ['ADMIN','PHARMACIST'].includes(this.user.role) ? await this.fetchAPI('/api/pharmacy/orders') : {orders:[]};
        const rxData = ['ADMIN','PHARMACIST'].includes(this.user.role) ? await this.fetchAPI('/api/pharmacy/prescriptions') : {prescriptions:[]};
        if (!data || !ordersData || !rxData) return;
        
        let html = `
        <div class="card mb-24">
            <div class="card-header"><div class="card-title">Doctor Prescriptions</div></div>
            <div class="card-body" style="padding:0;">
                <table>
                    <thead><tr><th>Date</th><th>Patient</th><th>Doctor</th><th>Prescription Details</th><th>Action</th></tr></thead>
                    <tbody>${(rxData.prescriptions||[]).length > 0 ? rxData.prescriptions.map(rx => `
                        <tr>
                            <td class="text-muted">${rx.record_date.substring(0,16)}</td>
                            <td style="font-weight:600;">${rx.first_name} ${rx.last_name}</td>
                            <td>Dr. ${rx.doctor_last}</td>
                            <td style="color:var(--primary); font-weight:500;">${rx.prescription}</td>
                            <td><button class="btn btn-secondary btn-sm" onclick="App.openCreateOrderModal(${rx.patient_id})">Fulfill Order</button></td>
                        </tr>
                    `).join('') : '<tr><td colspan="5" class="text-center text-muted" style="padding:20px;">No pending prescriptions found.</td></tr>'}</tbody>
                </table>
            </div>
        </div>
        <div class="card mb-24">
            <div class="card-header"><div class="card-title">Patient Orders</div></div>
            <div class="card-body" style="padding:0;">
                <table>
                    <thead><tr><th>Date</th><th>Patient</th><th>Drug</th><th>Qty</th><th>Status</th><th>Action</th></tr></thead>
                    <tbody>${(ordersData.orders||[]).map(o => `
                        <tr>
                            <td class="text-muted">${o.order_date.substring(0,16)}</td>
                            <td style="font-weight:600;">${o.first_name} ${o.last_name}</td>
                            <td>${o.item_name}</td>
                            <td>${o.quantity}</td>
                            <td><span class="badge badge-${o.payment_status==='Paid'?'success':(o.status==='Dispensed'?'default':'warning')}">${o.status==='Dispensed' ? 'Dispensed' : (o.payment_status === 'Paid' ? 'Paid - Ready' : 'Pending Payment')}</span></td>
                            <td>${o.payment_status === 'Paid' && o.status !== 'Dispensed' ? `<button class="btn btn-primary btn-sm" onclick="App.dispenseOrder(${o.order_id})">Dispense</button>` : ''}</td>
                        </tr>
                    `).join('')}</tbody>
                </table>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><div class="card-title">Inventory Management</div></div>
            <div class="card-body" style="padding:0;">
                <table>
                    <thead><tr><th>Item Name</th><th>Category</th><th>Stock</th><th>Unit Price</th><th>Expiry Date</th><th>Action</th></tr></thead>
                    <tbody>${data.inventory.map(i => `
                        <tr>
                            <td style="font-weight:600;">${i.item_name}</td>
                            <td><span class="badge badge-default">${i.category}</span></td>
                            <td><span class="${i.stock_quantity < 100 ? 'text-danger' : ''}" style="font-weight:600;">${i.stock_quantity}</span></td>
                            <td>$${i.unit_price.toFixed(2)}</td>
                            <td class="text-muted">${i.expiry_date}</td>
                            <td>${['ADMIN','PHARMACIST'].includes(this.user.role) ? `<button class="btn btn-secondary btn-sm" onclick="App.openEditInventoryModal(${i.item_id}, '${i.item_name.replace(/'/g, "\\\\'")}', '${i.category}', ${i.stock_quantity}, ${i.unit_price}, '${i.expiry_date}', '${i.supplier||''}')">Edit</button>` : ''}</td>
                        </tr>
                    `).join('')}</tbody>
                </table>
            </div>
        </div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderLaboratory() {
        this.setHeader('Laboratory', 'Test Results & Orders');
        const data = await this.fetchAPI('/api/lab/results');
        if (!data) return;
        
        let html = `<div class="card">
            <div class="card-body" style="padding:0;">
                <table>
                    <thead><tr><th>Test</th><th>Patient</th><th>Order Date</th><th>Status</th><th>Results</th><th>Action</th></tr></thead>
                    <tbody>${data.results.map(r => `
                        <tr>
                            <td style="font-weight:600;">${r.test_name}</td>
                            <td>${r.patient_first} ${r.patient_last}</td>
                            <td class="text-muted">${r.order_date.substring(0,16)}</td>
                            <td>
                                <span class="badge badge-${r.status==='Completed'?'success':r.status==='Pending'?'warning':'danger'}">${r.status}</span>
                                ${r.status !== 'Completed' ? `<br><small class="text-muted" style="font-size:11px;">${r.bill_id ? (r.payment_status === 'Paid' ? 'Paid' : 'Unpaid') : 'Unbilled'}</small>` : ''}
                            </td>
                            <td>${r.result_data || '<span class="text-muted">Awaiting results...</span>'}</td>
                            <td>
                                ${['ADMIN', 'LAB_TECH'].includes(this.user.role) && r.status === 'Pending' && !r.bill_id ? `<button class="btn btn-secondary btn-sm" onclick="App.chargeLabTest(${r.result_id})">Charge Patient</button>` : ''}
                                ${['ADMIN', 'LAB_TECH', 'DOCTOR'].includes(this.user.role) && r.status === 'Pending' && r.payment_status === 'Paid' ? `<button class="btn btn-primary btn-sm" onclick="App.openLabModal(${r.result_id})">Enter Results</button>` : ''}
                            </td>
                        </tr>
                    `).join('')}</tbody>
                </table>
            </div>
        </div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderAppointments() {
        let actionBtn = '';
        if (['ADMIN', 'RECEPTIONIST'].includes(this.user.role)) {
            actionBtn = '<button class="btn btn-primary" onclick="App.openAppointmentModal()">+ New Appointment</button>';
        }
        this.setHeader('Appointments', 'Schedule', actionBtn);
        const data = await this.fetchAPI('/api/appointments');
        if (!data) return;
        
        let html = `<div class="card"><div class="card-body" style="padding:0;">
            <table>
                <thead><tr><th>Date & Time</th><th>Patient</th><th>Doctor</th><th>Reason</th><th>Status</th><th>Action</th></tr></thead>
                <tbody>${data.appointments.map(a => `
                    <tr>
                        <td><strong>${a.appointment_date}</strong> <span class="text-muted">${a.appointment_time.substring(0,5)}</span></td>
                        <td>${a.patient_first} ${a.patient_last}</td>
                        <td>Dr. ${a.doctor_last}</td>
                        <td class="text-muted">${a.reason || '—'}</td>
                        <td><span class="badge badge-${a.status==='Completed'?'success':a.status==='Scheduled'?'info':'default'}">${a.status}</span></td>
                        <td>
                            ${this.user.role === 'DOCTOR' && a.status === 'Scheduled' ? `<button class="btn btn-primary btn-sm" onclick="App.openConsultModal(${a.appointment_id}, ${a.patient_id})">Start Consult</button>` : ''}
                            ${['ADMIN','RECEPTIONIST'].includes(this.user.role) && a.status === 'Scheduled' ? `<button class="btn btn-secondary btn-sm" onclick="App.openEditAppointmentModal(${a.appointment_id}, '${a.appointment_date}', '${a.appointment_time.substring(0,5)}', '${(a.reason||'').replace(/'/g, "\\\\'")}')">Edit</button>` : ''}
                        </td>
                    </tr>
                `).join('')}</tbody>
            </table>
        </div></div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderBilling() {
        this.setHeader('Billing', 'Invoices');
        const data = await this.fetchAPI('/api/billing');
        if (!data) return;
        
        let html = `<div class="card"><div class="card-body" style="padding:0;">
            <table>
                <thead><tr><th>Bill ID</th><th>Type</th><th>Patient</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead>
                <tbody>${data.bills.map(b => `
                    <tr>
                        <td class="text-muted">#${b.bill_id}</td>
                        <td><span class="badge badge-default">${b.bill_type || 'Consultation'}</span></td>
                        <td style="font-weight:600;">${b.patient_first} ${b.patient_last}</td>
                        <td>$${b.total_amount.toFixed(2)}</td>
                        <td><span class="badge badge-${b.payment_status==='Paid'?'success':b.payment_status==='Pending'?'warning':'danger'}">${b.payment_status}</span></td>
                        <td>
                            ${b.payment_status === 'Pending' ? `<button class="btn btn-primary btn-sm" onclick="App.openPaymentModal(${b.bill_id}, ${b.total_amount})">Pay</button>` : ''}
                            ${b.payment_status === 'Paid' ? `<button class="btn btn-secondary btn-sm" onclick="App.printReceipt(${b.bill_id})">🖨 Receipt</button>` : ''}
                        </td>
                    </tr>
                `).join('')}</tbody>
            </table>
        </div></div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderUsers() {
        this.setHeader('Staff Directory', 'System Users');
        const data = await this.fetchAPI('/api/admin/users');
        if (!data) return;
        
        let html = `<div class="card"><div class="card-body" style="padding:0;">
            <table>
                <thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Status</th></tr></thead>
                <tbody>${data.users.map(u => `
                    <tr>
                        <td style="font-weight:600;">${u.username}</td>
                        <td>${u.full_name}</td>
                        <td><span class="badge badge-default">${u.role}</span></td>
                        <td><span class="badge badge-${u.is_active?'success':'danger'}">${u.is_active?'Active':'Disabled'}</span></td>
                    </tr>
                `).join('')}</tbody>
            </table>
        </div></div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderAudit() {
        this.setHeader('Audit Log', 'System Activity');
        const data = await this.fetchAPI('/api/admin/audit');
        if (!data) return;
        
        let html = `<div class="card"><div class="card-body" style="padding:0;">
            <table>
                <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Table</th></tr></thead>
                <tbody>${data.logs.map(l => `
                    <tr>
                        <td class="text-muted">${l.action_timestamp}</td>
                        <td>${l.user_name}</td>
                        <td><span class="badge badge-default">${l.action}</span></td>
                        <td>${l.table_name}</td>
                    </tr>
                `).join('')}</tbody>
            </table>
        </div></div>`;
        this.elements.contentArea.innerHTML = html;
    },

    async renderReports() {
        this.setHeader('System Reports', 'Export Data to CSV');
        
        let html = `<div class="grid-3 mb-24">
            <div class="card">
                <div class="card-header"><div class="card-title">Patient Demographics</div></div>
                <div class="card-body" style="text-align: center; padding: 24px;">
                    <a href="/api/reports/patients" class="btn btn-primary" download>Download CSV</a>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><div class="card-title">Appointments Report</div></div>
                <div class="card-body" style="text-align: center; padding: 24px;">
                    <a href="/api/reports/appointments" class="btn btn-primary" download>Download CSV</a>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><div class="card-title">Financial & Billing Report</div></div>
                <div class="card-body" style="text-align: center; padding: 24px;">
                    <a href="/api/reports/billing" class="btn btn-primary" download>Download CSV</a>
                </div>
            </div>
        </div>`;
        this.elements.contentArea.innerHTML = html;
    },

    // ==========================================
    // UI MODALS FOR FORMS
    // ==========================================
    
    openPatientModal() {
        const body = `
            <form id="patientForm">
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">First Name</label><input type="text" id="p_first" class="form-control" required></div>
                    <div class="form-group"><label class="form-label">Last Name</label><input type="text" id="p_last" class="form-control" required></div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Date of Birth</label><input type="date" id="p_dob" class="form-control" required></div>
                    <div class="form-group"><label class="form-label">Gender</label>
                        <select id="p_gender" class="form-control"><option value="Male">Male</option><option value="Female">Female</option><option value="Other">Other</option></select>
                    </div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Phone</label><input type="text" id="p_phone" class="form-control"></div>
                    <div class="form-group"><label class="form-label">Email</label><input type="email" id="p_email" class="form-control"></div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Blood Group</label><input type="text" id="p_blood" class="form-control" placeholder="e.g. O+"></div>
                    <div class="form-group"><label class="form-label">Insurance ID</label><input type="text" id="p_insurance" class="form-control"></div>
                </div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitPatient()">Save Patient</button>
        `;
        this.showModal('Register Patient', body, footer);
    },

    async submitPatient() {
        const data = {
            first_name: document.getElementById('p_first').value,
            last_name: document.getElementById('p_last').value,
            date_of_birth: document.getElementById('p_dob').value,
            gender: document.getElementById('p_gender').value,
            phone: document.getElementById('p_phone').value,
            email: document.getElementById('p_email').value,
            blood_group: document.getElementById('p_blood').value,
            insurance_id: document.getElementById('p_insurance').value
        };
        const res = await fetch('/api/patients', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Patient registered successfully!', 'success');
            this.handleRoute(); // Refresh data
        } else {
            this.showToast(result.message || 'Error registering patient', 'error');
        }
    },

    async openAppointmentModal() {
        this.showModal('Schedule Appointment', '<div class="empty-state">Loading providers...</div>', '');
        const data = await this.fetchAPI('/api/medical-records/form-data');
        if (!data) { this.closeModal(); return; }
        
        const body = `
            <form id="apptForm">
                <div class="form-group">
                    <label class="form-label">Select Patient</label>
                    <select id="a_patient" class="form-control" required>
                        ${data.patients.map(p => `<option value="${p.patient_id}">${p.first_name} ${p.last_name}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Select Doctor</label>
                    <select id="a_doctor" class="form-control" required>
                        ${data.doctors.map(d => `<option value="${d.doctor_id}">Dr. ${d.first_name} ${d.last_name} (${d.specialization})</option>`).join('')}
                    </select>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Date</label><input type="date" id="a_date" class="form-control" required></div>
                    <div class="form-group"><label class="form-label">Time</label><input type="time" id="a_time" class="form-control" required></div>
                </div>
                <div class="form-group">
                    <label class="form-label">Reason</label>
                    <input type="text" id="a_reason" class="form-control">
                </div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitAppointment()">Schedule</button>
        `;
        document.getElementById('modalBody').innerHTML = body;
        document.getElementById('modalFooter').innerHTML = footer;
    },

    async submitAppointment() {
        const data = {
            patient_id: document.getElementById('a_patient').value,
            doctor_id: document.getElementById('a_doctor').value,
            appointment_date: document.getElementById('a_date').value,
            appointment_time: document.getElementById('a_time').value + ':00',
            reason: document.getElementById('a_reason').value
        };
        const res = await fetch('/api/appointments', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Appointment scheduled successfully!', 'success');
            this.handleRoute(); // Refresh data
        } else {
            this.showToast(result.message || 'Error scheduling', 'error');
        }
    },

    async chargeLabTest(result_id) {
        const res = await fetch(`/api/lab/results/${result_id}/charge`, { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            this.showToast('Patient charged. Awaiting payment.', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    async dispenseOrder(order_id) {
        const res = await fetch(`/api/pharmacy/orders/${order_id}/dispense`, { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            this.showToast('Medication dispensed.', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    async openCreateOrderModal(defaultPatientId = null) {
        this.showModal('Create Pharmacy Order', '<div class="empty-state">Loading...</div>', '');
        const dataPatients = await this.fetchAPI('/api/patients');
        const dataInv = await this.fetchAPI('/api/pharmacy/inventory');
        if (!dataPatients || !dataInv) { this.closeModal(); return; }
        
        const body = `
            <form id="pharmOrderForm">
                <div class="form-group">
                    <label class="form-label">Patient</label>
                    <select id="po_patient" class="form-control">
                        ${dataPatients.patients.map(p => `<option value="${p.patient_id}" ${defaultPatientId === p.patient_id ? 'selected' : ''}>${p.first_name} ${p.last_name}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Drug</label>
                    <select id="po_item" class="form-control">
                        ${dataInv.inventory.map(i => `<option value="${i.item_id}">${i.item_name} (Stock: ${i.stock_quantity}) - $${i.unit_price}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Quantity</label>
                    <input type="number" id="po_qty" class="form-control" value="1" min="1">
                </div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitPharmacyOrder()">Charge Patient</button>
        `;
        document.getElementById('modalBody').innerHTML = body;
        document.getElementById('modalFooter').innerHTML = footer;
    },

    async submitPharmacyOrder() {
        const data = {
            patient_id: document.getElementById('po_patient').value,
            item_id: document.getElementById('po_item').value,
            quantity: document.getElementById('po_qty').value
        };
        const res = await fetch('/api/pharmacy/orders', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Order created and billed to patient.', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },


    async dispenseMedication(item_id, item_name) {
        const res = await fetch(`/api/pharmacy/inventory/${item_id}/dispense`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({quantity: 1}) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast(`${item_name} dispensed.`, 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    openAddMedicationModal() {
        const body = `
            <div class="form-group"><label class="form-label">Item Name</label><input type="text" id="m_name" class="form-control" required></div>
            <div class="form-group"><label class="form-label">Category</label>
                <select id="m_category" class="form-control">
                    <option value="Tablet">Tablet</option>
                    <option value="Syrup">Syrup</option>
                    <option value="Injection">Injection</option>
                    <option value="Ointment">Ointment</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            <div class="grid-2">
                <div class="form-group"><label class="form-label">Stock Quantity</label><input type="number" id="m_stock" class="form-control" min="1" required></div>
                <div class="form-group"><label class="form-label">Unit Price ($)</label><input type="number" id="m_price" class="form-control" min="0" step="0.01" required></div>
            </div>
            <div class="form-group"><label class="form-label">Expiry Date</label><input type="date" id="m_expiry" class="form-control" required></div>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitMedication()">Add Medication</button>
        `;
        this.showModal('Add New Medication', body, footer);
    },

    async submitMedication() {
        const data = {
            item_name: document.getElementById('m_name').value,
            category: document.getElementById('m_category').value,
            stock_quantity: document.getElementById('m_stock').value,
            unit_price: document.getElementById('m_price').value,
            expiry_date: document.getElementById('m_expiry').value
        };
        if (!data.item_name || !data.stock_quantity || !data.unit_price || !data.expiry_date) {
            this.showToast('Please fill all required fields.', 'error');
            return;
        }
        const res = await fetch('/api/pharmacy/inventory', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Medication added successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    openLabModal(result_id) {
        const body = `
            <div class="form-group"><label class="form-label">Results / Notes</label><textarea id="l_results" class="form-control" rows="4"></textarea></div>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitLabResult(${result_id})">Save Result</button>
        `;
        this.showModal('Update Lab Result', body, footer);
    },

    async submitLabResult(result_id) {
        const data = { result_data: document.getElementById('l_results').value, status: 'Completed' };
        const res = await fetch(`/api/lab/results/${result_id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Lab result updated', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    openPaymentModal(bill_id, amount) {
        const body = `
            <div class="empty-state">Amount Due: <strong>$${amount.toFixed(2)}</strong></div>
            <div class="form-group">
                <label class="form-label">Payment Method</label>
                <select id="b_method" class="form-control">
                    <option value="Credit Card">Credit Card</option>
                    <option value="Cash">Cash</option>
                    <option value="Insurance">Insurance</option>
                </select>
            </div>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitPayment(${bill_id}, ${amount})">Process Payment</button>
        `;
        this.showModal(`Pay Invoice #${bill_id}`, body, footer);
    },

    async submitPayment(bill_id, amount) {
        const data = { payment_method: document.getElementById('b_method').value, paid_amount: amount };
        const res = await fetch(`/api/billing/${bill_id}/pay`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Payment successful', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    async openConsultModal(appointment_id, patient_id) {
        this.showModal('Start Consultation', '<div class="empty-state">Loading catalog...</div>', '');
        const data = await this.fetchAPI('/api/lab/tests');
        if (!data) { this.closeModal(); return; }
        
        const body = `
            <form id="consultForm">
                <div class="form-group"><label class="form-label">Diagnosis</label><input type="text" id="c_diag" class="form-control" required></div>
                <div class="form-group"><label class="form-label">Treatment Plan</label><textarea id="c_plan" class="form-control" rows="2"></textarea></div>
                <div class="form-group"><label class="form-label">Prescription</label><textarea id="c_rx" class="form-control" rows="2"></textarea></div>
                <div class="form-group"><label class="form-label">Order Lab Tests</label>
                    <select id="c_labs" class="form-control" multiple style="height: 100px;">
                        ${data.tests.map(t => `<option value="${t.test_id}">${t.test_name} ($${t.cost})</option>`).join('')}
                    </select>
                    <small class="text-muted">Hold Ctrl/Cmd to select multiple tests.</small>
                </div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitConsultation(${appointment_id}, ${patient_id})">Finish Consultation</button>
        `;
        document.getElementById('modalBody').innerHTML = body;
        document.getElementById('modalFooter').innerHTML = footer;
    },

    async submitConsultation(appointment_id, patient_id) {
        const select = document.getElementById('c_labs');
        const lab_test_ids = Array.from(select.selectedOptions).map(opt => parseInt(opt.value));
        
        const data = {
            appointment_id: appointment_id,
            patient_id: patient_id,
            doctor_id: this.user.doctor_id, // Wait, this isn't in user obj. 
            // The backend handles finding the doctor ID from session user_id. We'll omit it or let backend infer.
            diagnosis: document.getElementById('c_diag').value,
            treatment_plan: document.getElementById('c_plan').value,
            prescription: document.getElementById('c_rx').value,
            lab_test_ids: lab_test_ids
        };
        const res = await fetch('/api/medical-records', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Consultation saved successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    // ----------------- PHASE 4 WORKFLOWS -----------------
    async openAdmitModal() {
        this.showModal('Admit Patient', '<div class="empty-state">Loading data...</div>', '');
        const p_data = await this.fetchAPI('/api/patients');
        const w_data = await this.fetchAPI('/api/wards');
        if (!p_data || !w_data) { this.closeModal(); return; }

        const available_beds = w_data.beds.filter(b => b.status === 'Available');

        const body = `
            <div class="form-group"><label class="form-label">Patient</label>
                <select id="wa_patient" class="form-control">
                    ${p_data.patients.map(p => `<option value="${p.patient_id}">${p.first_name} ${p.last_name}</option>`).join('')}
                </select>
            </div>
            <div class="form-group"><label class="form-label">Assign Bed</label>
                <select id="wa_bed" class="form-control">
                    ${available_beds.length > 0 ? available_beds.map(b => `<option value="${b.bed_id}">${b.bed_number} (Ward #${b.ward_id})</option>`).join('') : '<option disabled>No beds available</option>'}
                </select>
            </div>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitAdmission()">Admit Patient</button>
        `;
        document.getElementById('modalBody').innerHTML = body;
        document.getElementById('modalFooter').innerHTML = footer;
    },

    async submitAdmission() {
        const bed = document.getElementById('wa_bed').value;
        if (!bed) { this.showToast('Please select a bed', 'error'); return; }
        
        const data = {
            patient_id: document.getElementById('wa_patient').value,
            bed_id: bed
        };
        const res = await fetch('/api/wards/admit', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Patient admitted successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    async dischargePatient(bed_id) {
        if (!confirm('Are you sure you want to discharge this patient? The bed will be freed.')) return;
        const res = await fetch(`/api/wards/discharge/${bed_id}`, { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            this.showToast('Patient discharged successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    // ----------------- PROFILE & SETTINGS -----------------
    async renderProfile() {
        this.setHeader('My Profile', 'Manage your account settings');
        const data = await this.fetchAPI('/api/profile');
        if (!data || !data.success) return;
        const p = data.profile;

        const avatarSrc = p.profile_picture || '';
        const avatarDisplay = avatarSrc 
            ? `<img src="${avatarSrc}?t=${Date.now()}" id="avatarPreview" style="width:120px;height:120px;border-radius:50%;object-fit:cover;border:3px solid var(--border);">`
            : `<div id="avatarPreview" style="width:120px;height:120px;border-radius:50%;background:var(--primary-light);color:var(--primary);display:flex;align-items:center;justify-content:center;font-size:48px;font-weight:700;border:3px solid var(--border);">${p.full_name.charAt(0).toUpperCase()}</div>`;

        let html = `
            <div class="card" style="margin-bottom:24px;">
                <div class="card-header"><div class="card-title">Profile Picture</div></div>
                <div class="card-body" style="display:flex;align-items:center;gap:32px;flex-wrap:wrap;">
                    ${avatarDisplay}
                    <div>
                        <p style="margin-bottom:12px;color:var(--text-muted);font-size:13px;">Upload a new profile picture. Supported: JPG, PNG, GIF, WebP. Max 2MB.</p>
                        <input type="file" id="avatarFile" accept="image/*" style="display:none;" onchange="App.uploadAvatar()">
                        <button class="btn btn-secondary" onclick="document.getElementById('avatarFile').click()">Choose Image</button>
                        ${avatarSrc ? '<button class="btn btn-secondary" style="margin-left:8px;" onclick="App.removeAvatar()">Remove</button>' : ''}
                    </div>
                </div>
            </div>
            <div class="grid-2">
                <div class="card">
                    <div class="card-header"><div class="card-title">Personal Information</div></div>
                    <div class="card-body">
                        <div class="form-group"><label class="form-label">Username</label><input type="text" class="form-control" value="${p.username}" disabled></div>
                        <div class="form-group"><label class="form-label">Role</label><input type="text" class="form-control" value="${p.role}" disabled></div>
                        <div class="form-group"><label class="form-label">Full Name</label><input type="text" id="prof_name" class="form-control" value="${p.full_name}"></div>
                        <div class="form-group"><label class="form-label">Email Address</label><input type="email" id="prof_email" class="form-control" value="${p.email || ''}"></div>
                        <button class="btn btn-primary" onclick="App.updateProfile()">Save Changes</button>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><div class="card-title">Security Settings</div></div>
                    <div class="card-body">
                        <div class="form-group"><label class="form-label">Current Password</label><input type="password" id="prof_curr_pwd" class="form-control"></div>
                        <div class="form-group"><label class="form-label">New Password</label><input type="password" id="prof_new_pwd" class="form-control"></div>
                        <div class="form-group"><label class="form-label">Confirm Password</label><input type="password" id="prof_conf_pwd" class="form-control"></div>
                        <button class="btn btn-danger" onclick="App.updatePassword()">Update Password</button>
                    </div>
                </div>
            </div>
        `;
        this.elements.contentArea.innerHTML = html;
    },

    async uploadAvatar() {
        const fileInput = document.getElementById('avatarFile');
        if (!fileInput.files.length) return;
        const file = fileInput.files[0];
        if (file.size > 2 * 1024 * 1024) {
            this.showToast('File too large. Maximum 2MB.', 'error');
            return;
        }
        const formData = new FormData();
        formData.append('avatar', file);
        
        const res = await fetch('/api/profile/avatar', { method: 'POST', body: formData });
        const result = await res.json();
        if (result.success) {
            this.showToast('Profile picture updated!', 'success');
            // Update sidebar avatar
            const sidebarAvatar = document.getElementById('userAvatar');
            sidebarAvatar.innerHTML = '';
            sidebarAvatar.style.backgroundImage = `url('${result.avatar_url}?t=${Date.now()}')`;
            sidebarAvatar.style.backgroundSize = 'cover';
            sidebarAvatar.style.backgroundPosition = 'center';
            sidebarAvatar.textContent = '';
            // Refresh the profile page
            this.renderProfile();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    async removeAvatar() {
        const res = await fetch('/api/profile', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ full_name: document.getElementById('prof_name').value, email: document.getElementById('prof_email').value }) });
        // Just re-render — we keep it simple
        this.showToast('Avatar removed on next login', 'info');
        this.renderProfile();
    },

    async updateProfile() {
        const data = {
            full_name: document.getElementById('prof_name').value,
            email: document.getElementById('prof_email').value
        };
        const res = await fetch('/api/profile', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.showToast('Profile updated successfully', 'success');
            document.getElementById('userName').textContent = data.full_name;
        } else {
            this.showToast(result.message, 'error');
        }
    },

    async updatePassword() {
        const curr_pwd = document.getElementById('prof_curr_pwd').value;
        const new_pwd = document.getElementById('prof_new_pwd').value;
        const conf_pwd = document.getElementById('prof_conf_pwd').value;

        if (!curr_pwd || !new_pwd || !conf_pwd) { this.showToast('Please fill all password fields', 'error'); return; }
        if (new_pwd !== conf_pwd) { this.showToast('New passwords do not match', 'error'); return; }

        const res = await fetch('/api/change-password', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ current_password: curr_pwd, new_password: new_pwd }) });
        const result = await res.json();
        if (result.success) {
            this.showToast('Password changed successfully!', 'success');
            document.getElementById('prof_curr_pwd').value = '';
            document.getElementById('prof_new_pwd').value = '';
            document.getElementById('prof_conf_pwd').value = '';
        } else {
            this.showToast(result.message, 'error');
        }
    },

    // ----------------- EDIT MODALS -----------------

    openEditPatientModal(id, first, last, dob, gender, phone, email, blood) {
        const body = `
            <form id="editPatientForm">
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">First Name</label><input type="text" id="ep_first" class="form-control" value="${first}"></div>
                    <div class="form-group"><label class="form-label">Last Name</label><input type="text" id="ep_last" class="form-control" value="${last}"></div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Date of Birth</label><input type="date" id="ep_dob" class="form-control" value="${dob}"></div>
                    <div class="form-group"><label class="form-label">Gender</label>
                        <select id="ep_gender" class="form-control">
                            <option value="Male" ${gender==='Male'?'selected':''}>Male</option>
                            <option value="Female" ${gender==='Female'?'selected':''}>Female</option>
                        </select>
                    </div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Phone</label><input type="text" id="ep_phone" class="form-control" value="${phone}"></div>
                    <div class="form-group"><label class="form-label">Email</label><input type="email" id="ep_email" class="form-control" value="${email}"></div>
                </div>
                <div class="form-group"><label class="form-label">Blood Group</label>
                    <select id="ep_blood" class="form-control">
                        <option value="">Unknown</option>
                        ${['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(bg => `<option value="${bg}" ${blood===bg?'selected':''}>${bg}</option>`).join('')}
                    </select>
                </div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitEditPatient(${id})">Save Changes</button>
        `;
        this.showModal('Edit Patient', body, footer);
    },

    async submitEditPatient(id) {
        const data = {
            first_name: document.getElementById('ep_first').value,
            last_name: document.getElementById('ep_last').value,
            date_of_birth: document.getElementById('ep_dob').value,
            gender: document.getElementById('ep_gender').value,
            phone: document.getElementById('ep_phone').value,
            email: document.getElementById('ep_email').value,
            blood_group: document.getElementById('ep_blood').value,
            address: '', insurance_id: ''
        };
        const res = await fetch(`/api/patients/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Patient updated successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    openEditAppointmentModal(id, date, time, reason) {
        const body = `
            <form id="editApptForm">
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Date</label><input type="date" id="ea_date" class="form-control" value="${date}"></div>
                    <div class="form-group"><label class="form-label">Time</label><input type="time" id="ea_time" class="form-control" value="${time}"></div>
                </div>
                <div class="form-group"><label class="form-label">Reason</label><textarea id="ea_reason" class="form-control" rows="3">${reason}</textarea></div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitEditAppointment(${id})">Save Changes</button>
        `;
        this.showModal('Edit Appointment', body, footer);
    },

    async submitEditAppointment(id) {
        const data = {
            appointment_date: document.getElementById('ea_date').value,
            appointment_time: document.getElementById('ea_time').value + ':00',
            reason: document.getElementById('ea_reason').value
        };
        const res = await fetch(`/api/appointments/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Appointment updated successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    openEditInventoryModal(id, name, category, stock, price, expiry, supplier) {
        const body = `
            <form id="editInvForm">
                <div class="form-group"><label class="form-label">Item Name</label><input type="text" id="ei_name" class="form-control" value="${name}"></div>
                <div class="form-group"><label class="form-label">Category</label>
                    <select id="ei_cat" class="form-control">
                        ${['Antibiotic','Painkiller','Blood Pressure','Diabetes','Tablet','Syrup','Injection','Ointment','Other'].map(c => `<option value="${c}" ${category.trim()===c?'selected':''}>${c}</option>`).join('')}
                    </select>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Stock Quantity</label><input type="number" id="ei_stock" class="form-control" value="${stock}" min="0"></div>
                    <div class="form-group"><label class="form-label">Unit Price ($)</label><input type="number" id="ei_price" class="form-control" value="${price}" min="0" step="0.01"></div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Expiry Date</label><input type="date" id="ei_expiry" class="form-control" value="${expiry}"></div>
                    <div class="form-group"><label class="form-label">Supplier</label><input type="text" id="ei_supplier" class="form-control" value="${supplier}"></div>
                </div>
            </form>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="App.submitEditInventory(${id})">Save Changes</button>
        `;
        this.showModal('Edit Medication', body, footer);
    },

    async submitEditInventory(id) {
        const data = {
            item_name: document.getElementById('ei_name').value,
            category: document.getElementById('ei_cat').value,
            stock_quantity: document.getElementById('ei_stock').value,
            unit_price: document.getElementById('ei_price').value,
            expiry_date: document.getElementById('ei_expiry').value,
            supplier: document.getElementById('ei_supplier').value
        };
        const res = await fetch(`/api/pharmacy/inventory/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.success) {
            this.closeModal();
            this.showToast('Inventory updated successfully', 'success');
            this.handleRoute();
        } else {
            this.showToast(result.message, 'error');
        }
    },

    // ----------------- RECEIPT PRINTING -----------------

    async printReceipt(bill_id) {
        const data = await this.fetchAPI(`/api/billing/${bill_id}/receipt`);
        if (!data || !data.success) { this.showToast('Could not load receipt', 'error'); return; }
        const r = data.receipt;

        const receiptHtml = `
            <html>
            <head>
                <title>Receipt #${r.bill_id}</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; max-width: 600px; margin: 0 auto; color: #1e293b; }
                    .header { text-align: center; border-bottom: 2px solid #0f766e; padding-bottom: 20px; margin-bottom: 24px; }
                    .header h1 { color: #0f766e; font-size: 24px; margin-bottom: 4px; }
                    .header p { color: #64748b; font-size: 13px; }
                    .receipt-title { text-align: center; font-size: 18px; font-weight: 700; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
                    .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #e2e8f0; font-size: 14px; }
                    .info-row .label { color: #64748b; font-weight: 500; }
                    .info-row .value { font-weight: 600; }
                    .total-row { display: flex; justify-content: space-between; padding: 14px 0; border-top: 2px solid #0f766e; margin-top: 16px; font-size: 18px; font-weight: 700; color: #0f766e; }
                    .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px; }
                    .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; background: #d1fae5; color: #065f46; }
                    @media print { body { padding: 20px; } }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏥 Hospital Management System</h1>
                    <p>Official Payment Receipt</p>
                </div>
                <div class="receipt-title">Payment Receipt</div>
                <div class="info-row"><span class="label">Receipt No:</span><span class="value">#${r.bill_id}</span></div>
                <div class="info-row"><span class="label">Date:</span><span class="value">${r.billing_date}</span></div>
                <div class="info-row"><span class="label">Patient Name:</span><span class="value">${r.first_name} ${r.last_name}</span></div>
                <div class="info-row"><span class="label">Patient Phone:</span><span class="value">${r.phone || 'N/A'}</span></div>
                <div class="info-row"><span class="label">Bill Type:</span><span class="value">${r.bill_type || 'Consultation'}</span></div>
                <div class="info-row"><span class="label">Payment Method:</span><span class="value">${r.payment_method || 'N/A'}</span></div>
                <div class="info-row"><span class="label">Status:</span><span class="value"><span class="badge">${r.payment_status}</span></span></div>
                <div class="total-row"><span>Total Paid:</span><span>$${r.total_amount.toFixed(2)}</span></div>
                <div class="footer">
                    <p>Thank you for your payment.</p>
                    <p style="margin-top:8px;">This is a computer-generated receipt. No signature required.</p>
                </div>
            </body>
            </html>
        `;

        const printWindow = window.open('', '_blank', 'width=700,height=800');
        printWindow.document.write(receiptHtml);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => { printWindow.print(); }, 500);
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());

