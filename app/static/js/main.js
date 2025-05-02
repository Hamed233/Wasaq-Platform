// Waqaf Platform - Main JavaScript File

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    })
    
    // Password strength meter
    const passwordInputs = document.querySelectorAll('input[type="password"][id="password"]');
    passwordInputs.forEach(function(input) {
        if (input) {
            input.addEventListener('input', function() {
                const password = this.value;
                const strengthMeter = this.parentElement.querySelector('.password-strength');
                
                if (strengthMeter) {
                    // Calculate password strength
                    let strength = 0;
                    if (password.length >= 8) strength += 1;
                    if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength += 1;
                    if (password.match(/[0-9]/)) strength += 1;
                    if (password.match(/[^a-zA-Z0-9]/)) strength += 1;
                    
                    // Update strength meter
                    strengthMeter.className = 'password-strength';
                    if (strength === 0) {
                        strengthMeter.classList.add('weak');
                        strengthMeter.textContent = 'ضعيفة جداً';
                    } else if (strength === 1) {
                        strengthMeter.classList.add('weak');
                        strengthMeter.textContent = 'ضعيفة';
                    } else if (strength === 2) {
                        strengthMeter.classList.add('medium');
                        strengthMeter.textContent = 'متوسطة';
                    } else if (strength === 3) {
                        strengthMeter.classList.add('strong');
                        strengthMeter.textContent = 'قوية';
                    } else {
                        strengthMeter.classList.add('very-strong');
                        strengthMeter.textContent = 'قوية جداً';
                    }
                }
            });
        }
    });
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.alert:not(.alert-permanent)');
    flashMessages.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Handle map initialization if map container exists
    const mapContainer = document.getElementById('map');
    if (mapContainer) {
        // Default to Saudi Arabia center coordinates
        const defaultLat = 24.7136;
        const defaultLng = 46.6753;
        const defaultZoom = 6;
        
        // Initialize Leaflet map
        const map = L.map('map').setView([defaultLat, defaultLng], defaultZoom);
        
        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        // If there are land markers data available, add them to the map
        if (typeof landMarkers !== 'undefined' && landMarkers.length > 0) {
            landMarkers.forEach(function(land) {
                const marker = L.marker([land.lat, land.lng]).addTo(map);
                marker.bindPopup(`
                    <strong>${land.title}</strong><br>
                    ${land.description}<br>
                    <a href="/lands/view/${land.id}" class="btn btn-sm btn-primary mt-2">عرض التفاصيل</a>
                `);
            });
            
            // Fit map bounds to markers if more than one
            if (landMarkers.length > 1) {
                const bounds = L.latLngBounds(landMarkers.map(land => [land.lat, land.lng]));
                map.fitBounds(bounds);
            }
        }
    }
    
    // Handle charts initialization if chart containers exist
    const chartContainers = document.querySelectorAll('[data-chart-type]');
    chartContainers.forEach(function(container) {
        const chartType = container.getAttribute('data-chart-type');
        const chartData = JSON.parse(container.getAttribute('data-chart-data') || '{}');
        const chartOptions = JSON.parse(container.getAttribute('data-chart-options') || '{}');
        
        if (chartType && chartData) {
            const ctx = container.getContext('2d');
            new Chart(ctx, {
                type: chartType,
                data: chartData,
                options: chartOptions
            });
        }
    });
});
