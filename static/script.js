document.addEventListener('DOMContentLoaded', function () {
    // --- Element Selections ---
    const form = document.getElementById('dietForm');
    const getLocationBtn = document.getElementById('getLocationBtn');
    const locationStatus = document.getElementById('locationStatus');
    const locationInput = document.getElementById('locationInput');
    const latitudeInput = document.getElementById('latitude');
    const longitudeInput = document.getElementById('longitude');

    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const errorMessageSpan = document.getElementById('errorMessage');
    const planContainer = document.getElementById('planContainer');
    const metaDataDiv = document.getElementById('metaData');
    const planOutputDiv = document.getElementById('planOutput');

    // Initialize Markdown to HTML converter if Showdown is loaded
    const converter = typeof showdown !== 'undefined' ? new showdown.Converter({
        tables: true,
        strikethrough: true,
        tasklists: true,
        simpleLineBreaks: true
    }) : null;

    if (!converter) {
        console.error("Showdown.js library not loaded. Markdown conversion will not work.");
    }

    // --- Geolocation Logic ---
    getLocationBtn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            locationStatus.textContent = 'Geolocation is not supported by your browser.';
            locationStatus.className = 'text-sm text-red-600 mt-2';
            return;
        }

        locationStatus.textContent = 'Fetching location...';
        locationStatus.className = 'text-sm text-blue-600 mt-2';
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                latitudeInput.value = latitude;
                longitudeInput.value = longitude;
                locationStatus.textContent = `Location captured successfully.`;
                locationStatus.className = 'text-sm text-green-700 mt-2';
                locationInput.value = ''; 
                locationInput.disabled = true;
                locationInput.placeholder = 'Using GPS location';
            },
            (error) => {
                let message = 'Could not fetch location. Please enter it manually.';
                locationStatus.textContent = message;
                locationStatus.className = 'text-sm text-red-600 mt-2';
                locationInput.disabled = false;
            }
        );
    });

    // --- Form Submission Logic ---
    form.addEventListener('submit', async function (event) {
        event.preventDefault();

        // Show loading state and scroll to results
        resultsDiv.classList.remove('hidden');
        loadingDiv.classList.remove('hidden');
        errorDiv.classList.add('hidden');
        planContainer.classList.add('hidden');
        window.scrollTo({ top: resultsDiv.offsetTop - 40, behavior: 'smooth' });

        const formData = new FormData(form);

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

            // Populate metadata
            metaDataDiv.innerHTML = `
                <h3 class="text-lg font-semibold font-sans !text-emerald-900 !border-none !m-0 !p-0">Your Plan Details</h3>
                <ul class="list-disc list-inside mt-2 text-sm">
                    <li><strong>Location:</strong> ${data.used_location}</li>
                    <li><strong>Weather:</strong> ${data.used_weather}</li>
                    <li><strong>Starting Day:</strong> ${data.current_day}</li>
                </ul>`;
            
            // Convert markdown plan to HTML and display
            if (converter) {
                const htmlPlan = converter.makeHtml(data.plan);
                planOutputDiv.innerHTML = htmlPlan;
            } else {
                // Fallback for if Showdown fails to load
                planOutputDiv.textContent = data.plan;
            }
            
            planContainer.classList.remove('hidden');

        } catch (err) {
            errorMessageSpan.textContent = err.message;
            errorDiv.classList.remove('hidden');
        } finally {
            loadingDiv.classList.add('hidden');
        }
    });
});
