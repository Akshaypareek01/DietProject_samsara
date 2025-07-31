document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('diet-form');
    const formContainer = document.getElementById('form-container');
    const nextButtons = document.querySelectorAll('.next-btn');
    const prevButtons = document.querySelectorAll('.back-btn');
    const questionGroups = document.querySelectorAll('.question-group');
    const progressBarFill = document.querySelector('.progress-bar-fill');
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('result-container');
    const container = document.querySelector('.container');

    let currentQuestion = 0;
    const totalQuestions = questionGroups.length;

    const updateProgress = () => {
        const progress = ((currentQuestion + 1) / totalQuestions) * 100;
        progressBarFill.style.width = `${progress}%`;
        const activeQuestionHeight = questionGroups[currentQuestion].offsetHeight;
        formContainer.style.height = `${activeQuestionHeight}px`;
    };

    const showQuestion = (index) => {
        questionGroups.forEach((group, i) => {
            group.classList.remove('active', 'previous');
            if (i < index) {
                group.classList.add('previous');
            }
        });
        questionGroups[index].classList.add('active');
        currentQuestion = index;
        updateProgress();
    };

    nextButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (currentQuestion < totalQuestions - 1) {
                showQuestion(currentQuestion + 1);
            }
        });
    });

    prevButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (currentQuestion > 0) {
                showQuestion(currentQuestion - 1);
            }
        });
    });

    form.addEventListener('submit', function(event) {
        event.preventDefault();

        document.getElementById('form-section').style.display = 'none';
        loading.style.display = 'block';
        container.style.height = 'auto';

        const formData = new FormData(form);

        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.error) {
                resultContainer.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
            } else {
                displayDietPlan(data.plan);
            }
            resultContainer.style.display = 'block';

            // --- THIS IS THE FIX FOR SCROLLING ---
            document.body.style.overflow = 'auto';

        })
        .catch(error => {
            loading.style.display = 'none';
            resultContainer.innerHTML = `<p style="color:red;">An unexpected error occurred. Please try again.</p>`;
            resultContainer.style.display = 'block';
            console.error('Error:', error);

            // --- ALSO ADD THE FIX HERE IN CASE OF ERROR ---
            document.body.style.overflow = 'auto';
        });
    });

    const displayDietPlan = (planText) => {
        resultContainer.innerHTML = '';

        const resultHeader = document.createElement('div');
        resultHeader.className = 'result-header';
        resultHeader.innerHTML = '<h2>Your Personalized Diet Plan</h2>';
        resultContainer.appendChild(resultHeader);

        const lines = planText.split('\n');
        let currentCard = null;

        lines.forEach(line => {
            line = line.trim();
            if (line.startsWith('###')) {
                if (currentCard) {
                    resultContainer.appendChild(currentCard);
                }
                currentCard = document.createElement('div');
                currentCard.className = 'meal-card';

                const title = document.createElement('h3');
                title.textContent = line.replace('###', '').trim();
                currentCard.appendChild(title);

            } else if (line && currentCard) {
                if(line.startsWith('**') || line.startsWith('-')){
                    const p = document.createElement('p');
                    p.innerHTML = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    currentCard.appendChild(p);
                } else {
                    const p = document.createElement('p');
                    p.textContent = line;
                    currentCard.appendChild(p);
                }
            }
        });

        if (currentCard) {
            resultContainer.appendChild(currentCard);
        }
    };

    showQuestion(0);
});
