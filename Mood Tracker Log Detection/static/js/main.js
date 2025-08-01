document.addEventListener('DOMContentLoaded', function() {
    // --- Theme Switcher ---
    const themeSwitcher = document.getElementById('theme-switcher');
    const body = document.body;

    const setTheme = (theme) => {
        body.classList.remove('light-mode', 'dark-mode');
        body.classList.add(theme + '-mode');
        localStorage.setItem('theme', theme);
    };

    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', () => {
            const currentTheme = localStorage.getItem('theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }

    // Apply saved theme on initial load
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);


    // --- Chart Initializations ---

    // Mood Frequency Bar Chart
    const moodChartCanvas = document.getElementById('moodChart');
    if (moodChartCanvas) {
        let year, month;
        if (moodChartCanvas.dataset.year && moodChartCanvas.dataset.month) {
            year = moodChartCanvas.dataset.year;
            month = moodChartCanvas.dataset.month;
        } else {
            const today = new Date();
            year = today.getFullYear();
            month = today.getMonth() + 1;
        }
        const apiUrl = `/api/mood-data?year=${year}&month=${month}`;

        fetch(apiUrl)
            .then(response => response.json())
            .then(data => {
                if (data.labels && data.labels.length > 0) {
                    const colorMap = {
                        'Happy': { background: 'rgba(255, 206, 86, 0.2)', border: 'rgba(255, 206, 86, 1)' },
                        'Sad': { background: 'rgba(54, 162, 235, 0.2)', border: 'rgba(54, 162, 235, 1)' },
                        'Excited': { background: 'rgba(153, 102, 255, 0.2)', border: 'rgba(153, 102, 255, 1)' },
                        'Love': { background: 'rgba(255, 99, 132, 0.2)', border: 'rgba(255, 99, 132, 1)' },
                        'Nice': { background: 'rgba(75, 192, 192, 0.2)', border: 'rgba(75, 192, 192, 1)' },
                        'Bad': { background: 'rgba(255, 159, 64, 0.2)', border: 'rgba(255, 159, 64, 1)' },
                        'Angry': { background: 'rgba(255, 0, 0, 0.2)', border: 'rgba(255, 0, 0, 1)' }
                    };
                    const backgroundColors = data.labels.map(label => colorMap[label]?.background || 'rgba(201, 203, 207, 0.2)');
                    const borderColors = data.labels.map(label => colorMap[label]?.border || 'rgba(201, 203, 207, 1)');
                    const ctx = moodChartCanvas.getContext('2d');
                    new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: 'Mood Frequency',
                                data: data.data,
                                backgroundColor: backgroundColors,
                                borderColor: borderColors,
                                borderWidth: 1
                            }]
                        },
                        options: { scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
                    });
                }
            });
    }

    // Monthly Trend Line Chart
    const monthlyTrendCanvas = document.getElementById('monthlyTrendChart');
    if (monthlyTrendCanvas) {
        let year, month;
        if (monthlyTrendCanvas.dataset.year && monthlyTrendCanvas.dataset.month) {
            year = monthlyTrendCanvas.dataset.year;
            month = monthlyTrendCanvas.dataset.month;
        } else {
            const today = new Date();
            year = today.getFullYear();
            month = today.getMonth() + 1;
        }
        const apiUrl = `/api/monthly-trend?year=${year}&month=${month}`;

        fetch(apiUrl)
            .then(response => response.json())
            .then(data => {
                if (data.data_available) {
                    const validDataPoints = data.data.filter(d => d !== null).length;
                    const chartType = validDataPoints === 1 ? 'bar' : 'line';

                    const ctx = monthlyTrendCanvas.getContext('2d');
                    new Chart(ctx, {
                        type: chartType,
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: 'Monthly Mood Trend',
                                data: data.data,
                                fill: false,
                                borderColor: 'rgb(75, 192, 192)',
                                backgroundColor: 'rgba(75, 192, 192, 0.5)', // For bar chart
                                tension: 0.1,
                                spanGaps: true // Connect lines over null data points
                            }]
                        },
                        options: {
                            scales: {
                                y: {
                                    suggestedMin: -3,
                                    suggestedMax: 3
                                }
                            }
                        }
                    });
                } else {
                    document.getElementById('monthlyTrendChart').style.display = 'none';
                    document.getElementById('no-trend-data').style.display = 'block';
                }
            });
    }

    // --- Chatbot ---
    const chatbot = document.getElementById('chatbot');
    const chatbotHeader = document.getElementById('chatbot-header');
    const chatbotBody = document.getElementById('chatbot-body');
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotMessages = document.getElementById('chatbot-messages');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSend = document.getElementById('chatbot-send');

    if (chatbot) {
        chatbotHeader.addEventListener('click', () => {
            if (chatbotBody.style.display === 'none' || chatbotBody.style.display === '') {
                chatbotBody.style.display = 'block';
                chatbotToggle.textContent = '−';
            } else {
                chatbotBody.style.display = 'none';
                chatbotToggle.textContent = '+';
            }
        });

        const sendMessage = () => {
            const messageText = chatbotInput.value.trim();
            if (messageText) {
                // Add user message to chat
                const userMessage = document.createElement('div');
                userMessage.classList.add('message', 'user');
                userMessage.textContent = messageText;
                chatbotMessages.appendChild(userMessage);
                chatbotInput.value = '';
                chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

                // Send message to backend
                fetch('/api/chatbot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: messageText })
                })
                .then(response => response.json())
                .then(data => {
                    const botMessage = document.createElement('div');
                    botMessage.classList.add('message', 'bot');
                    botMessage.textContent = data.reply;
                    chatbotMessages.appendChild(botMessage);
                    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

                    // Handle chart scrolling action
                    if (data.action === 'show_chart' && data.chart_id) {
                        const chartElement = document.getElementById(data.chart_id);
                        if (chartElement) {
                            chartElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            // Highlight the chart briefly
                            chartElement.style.transition = 'box-shadow 0.5s ease-in-out';
                            chartElement.style.boxShadow = '0 0 20px rgba(75, 192, 192, 0.8)';
                            setTimeout(() => {
                                chartElement.style.boxShadow = '';
                            }, 2000);
                        }
                    }
                });
            }
        };

        chatbotSend.addEventListener('click', sendMessage);
        chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});
