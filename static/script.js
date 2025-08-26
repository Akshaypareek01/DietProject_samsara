document.addEventListener('DOMContentLoaded', function () {
    // --- Element Selections ---
    const form = document.getElementById('dietForm');
    const getLocationBtn = document.getElementById('getLocationBtn');
    const locationStatus = document.getElementById('locationStatus');
    const locationInput = document.getElementById('locationInput');
    const latitudeInput = document.getElementById('latitude');
    const longitudeInput = document.getElementById('longitude');

    // New element selections for BMI calculation
    const heightInput = document.getElementById('height');
    const weightInput = document.getElementById('weight');
    const bmiInput = document.getElementById('bmi');

    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const errorMessageSpan = document.getElementById('errorMessage');
    const planContainer = document.getElementById('planContainer');
    const metaDataDiv = document.getElementById('metaData');
    const planOutputDiv = document.getElementById('planOutput');

    const converter = typeof showdown !== 'undefined' ? new showdown.Converter({
        tables: true,
        strikethrough: true,
        tasklists: true,
        simpleLineBreaks: true
    }) : null;

    // --- NEW: BMI Calculation Logic ---
    function calculateBmi() {
        const height = parseFloat(heightInput.value);
        const weight = parseFloat(weightInput.value);

        if (height > 0 && weight > 0) {
            const heightInMeters = height / 100;
            const bmi = weight / (heightInMeters * heightInMeters);
            bmiInput.value = bmi.toFixed(1); // Display BMI with one decimal place
        } else {
            bmiInput.value = ''; // Clear if inputs are invalid
        }
    }

    // Add event listeners to height and weight fields
    heightInput.addEventListener('input', calculateBmi);
    weightInput.addEventListener('input', calculateBmi);


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
                locationStatus.textContent = 'Could not fetch location. Please enter it manually.';
                locationStatus.className = 'text-sm text-red-600 mt-2';
                locationInput.disabled = false;
            }
        );
    });

    // --- Form Submission Logic ---
    form.addEventListener('submit', async function (event) {
        event.preventDefault();
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

            metaDataDiv.innerHTML = `
                <h3 class="text-lg font-semibold font-sans !text-emerald-900 !border-none !m-0 !p-0">Your Plan Details</h3>
                <ul class="list-disc list-inside mt-2 text-sm">
                    <li><strong>Location:</strong> ${data.used_location}</li>
                    <li><strong>Weather:</strong> ${data.used_weather}</li>
                    <li><strong>Starting Day:</strong> ${data.current_day}</li>
                </ul>`;
            
            if (converter) {
                const htmlPlan = converter.makeHtml(data.plan);
                planOutputDiv.innerHTML = htmlPlan;
            } else {
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
