/**
 * Sentiment results display and data fetching
 */

/**
 * Fetch sentiment data for all countries
 */
function fetchAllSentimentData() {
    fetch('/api/results')
        .then(response => response.json())
        .then(data => {
            updateMarkers(data);
        })
        .catch(error => {
            console.error('Error fetching all sentiment data:', error);
        });
}

/**
 * Fetch sentiment data for a specific country
 */
function fetchCountrySentiment(country) {
    fetch(`/api/results/${country}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    return Promise.reject('No data available for this country yet.');
                }
                return Promise.reject(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            displayCountryResults(data);
            // After displaying sentiment data, fetch ACLED data
            fetchAcledData(country);
        })
        .catch(error => {
            console.error('Error fetching country sentiment data:', error);
            document.getElementById('country-details').innerHTML = `
                <div class="alert alert-warning">
                    <h3>No Data Available</h3>
                    <p>${error || 'Sentiment analysis has not been run for this country yet.'}</p>
                    <button id="run-analysis-btn" class="btn btn-primary" onclick="triggerAnalysis('${country}')">
                        Run Analysis Now
                    </button>
                </div>
            `;
        });
}

/**
 * Fetch ACLED violent events data for a country
 */
function fetchAcledData(country) {
    // Show loading state
    document.getElementById('acled-loading').style.display = 'block';
    document.getElementById('acled-data').style.display = 'none';
    
    fetch(`/api/acled/${country}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 404) {
                    return Promise.reject('No ACLED data available for this country.');
                }
                return Promise.reject(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            displayAcledData(data);
        })
        .catch(error => {
            console.error('Error fetching ACLED data:', error);
            document.getElementById('acled-content').innerHTML = `
                <div class="alert alert-warning">
                    <p>${error || 'ACLED violent events data is not available for this country.'}</p>
                </div>
            `;
        });
}

/**
 * Display ACLED data visualization
 */
function displayAcledData(acledData) {
    if (!acledData || !acledData.has_data) {
        const acledContainer = document.getElementById('acled-content');
        if (acledContainer) {
            acledContainer.innerHTML = `
                <div class="alert alert-warning">
                    <p>No ACLED data available for this country.</p>
                </div>
            `;
        }
        return;
    }
    
    // Hide loading indicator and show data container
    const loadingElement = document.getElementById('acled-loading');
    const dataElement = document.getElementById('acled-data');
    
    if (loadingElement) loadingElement.style.display = 'none';
    if (dataElement) dataElement.style.display = 'block';
    
    // Set event count
    const eventCountElement = document.getElementById('event-count');
    if (eventCountElement) {
        eventCountElement.textContent = acledData.weekly_events || 0;
    }
    
    // Set fatality count
    const fatalityCountElement = document.getElementById('fatality-count');
    if (fatalityCountElement) {
        fatalityCountElement.textContent = acledData.weekly_fatalities || 0;
    }
    
    // Update trends if available
    if (acledData.events_trend_pct) {
        updateTrendIndicator('events', acledData.events_trend_pct);
    }
    
    if (acledData.fatalities_trend_pct) {
        updateTrendIndicator('fatalities', acledData.fatalities_trend_pct);
    }
    
    // Show alerts if any
    const alertsElement = document.getElementById('acled-alerts');
    const alertBadge = document.getElementById('acled-alert-badge');
    
    if (acledData.has_anomalies && alertsElement && alertBadge) {
        alertsElement.style.display = 'block';
        alertBadge.style.display = 'inline-block';
        
        const alertsList = document.getElementById('acled-alerts-list');
        if (alertsList && acledData.anomalies) {
            alertsList.innerHTML = '';
            acledData.anomalies.forEach(alert => {
                const li = document.createElement('li');
                li.textContent = alert;
                alertsList.appendChild(li);
            });
        }
    } else {
        if (alertsElement) alertsElement.style.display = 'none';
        if (alertBadge) alertBadge.style.display = 'none';
    }
    
    // Update chart image if available
    const chartContainer = document.getElementById('acled-chart-container');
    const chartImage = document.getElementById('acled-chart');
    
    if (chartContainer && chartImage) {
        if (acledData.chart_path) {
            chartImage.src = acledData.chart_path;
            chartContainer.style.display = 'block';
            
            // Make chart clickable and show cursor pointer
            chartImage.style.cursor = 'pointer';
            
            // Add click event to show modal with larger chart
            chartImage.onclick = function() {
                const largeChart = document.getElementById('acled-chart-large');
                largeChart.src = acledData.chart_path;
                
                // Update modal title to include country name
                const modalTitle = document.getElementById('acledChartModalLabel');
                const countryName = document.getElementById('country-name').textContent;
                modalTitle.textContent = `${countryName}: Weekly Violent Events & Fatalities`;
                
                // Show the modal
                const chartModal = new bootstrap.Modal(document.getElementById('acledChartModal'));
                chartModal.show();
            };
            
            // Update labels to indicate weekly data
            const eventLabel = document.querySelector('.stat-box .stat-label.event-label');
            if (eventLabel) {
                eventLabel.textContent = 'Weekly Violent Events';
            }
            
            const fatalityLabel = document.querySelector('.stat-box .stat-label.fatality-label');
            if (fatalityLabel) {
                fatalityLabel.textContent = 'Weekly Fatalities';
            }
        } else {
            chartContainer.style.display = 'none';
        }
    }
}

/**
 * Update trend indicator with appropriate icon and color
 */
function updateTrendIndicator(type, trendPct) {
    const iconElement = document.getElementById(`${type}-trend-icon`);
    const valueElement = document.getElementById(`${type}-trend-value`);
    
    if (trendPct === null || trendPct === undefined) {
        iconElement.innerHTML = '';
        valueElement.textContent = 'No trend data';
        return;
    }
    
    let icon, className;
    
    if (trendPct > 0) {
        // Rising trend (bad for violent events)
        icon = '↑';
        className = 'trend-up';
        valueElement.textContent = `+${trendPct}%`;
    } else if (trendPct < 0) {
        // Falling trend (good for violent events)
        icon = '↓';
        className = 'trend-down';
        valueElement.textContent = `${trendPct}%`;
    } else {
        // No change
        icon = '→';
        className = 'trend-neutral';
        valueElement.textContent = '0%';
    }
    
    iconElement.innerHTML = icon;
    iconElement.className = className;
    valueElement.className = className;
}

/**
 * Update the sentiment meter classes based on the sentiment score
 */
function updateSentimentMeterClasses(score) {
    // Position the sentiment pointer (convert -2 to 2 scale to 0 to 100%)
    // Ensure the value stays within bounds even if outside normal range
    let normalizedScore = Math.max(-2, Math.min(2, score));
    const pointerPosition = ((normalizedScore + 2) / 4) * 100;
    
    const pointerElement = document.getElementById('sentiment-pointer');
    if (pointerElement) {
        pointerElement.style.left = `${pointerPosition}%`;
    }
    
    // Update the meter class based on the sentiment score
    const meterElement = document.getElementById('sentiment-meter-bar');
    if (!meterElement) return;
    
    // Remove any existing sentiment classes
    meterElement.classList.remove('very-negative', 'negative', 'neutral', 'positive', 'very-positive');
    
    // Add the appropriate class based on the score
    if (score < -1.5) {
        meterElement.classList.add('very-negative');
    } else if (score < -0.5) {
        meterElement.classList.add('negative');
    } else if (score <= 0.5) {
        meterElement.classList.add('neutral');
    } else if (score <= 1.5) {
        meterElement.classList.add('positive');
    } else {
        meterElement.classList.add('very-positive');
    }
}

/**
 * Format and display a summary
 */
function formatAndDisplaySummary(summary, container) {
    if (!summary) {
        container.innerHTML = '<p>No summary available.</p>';
        return;
    }
    
    let formattedSummary = summary;
    
    // Add colors for section headings (handle different formats)
    formattedSummary = formattedSummary.replace(/(SECTION \d+:?\s*NEGATIVE NEWS SUMMARY|NEGATIVE NEWS SUMMARY)/gi, 
        '<h3 class="summary-section negative-section">$1</h3>');
    
    formattedSummary = formattedSummary.replace(/(SECTION \d+:?\s*POSITIVE NEWS SUMMARY|POSITIVE NEWS SUMMARY)/gi, 
        '<h3 class="summary-section positive-section">$1</h3>');
    
    // Style the numbered points (handle different formats)
    formattedSummary = formattedSummary.replace(/(\d+\.\s*)(.*?)(?::\s*|\n)/g, 
        '<h4 class="summary-point">$1$2</h4>');
    
    // Style the bullet points and distinguish between sections
    let lines = formattedSummary.split('\n');
    let inPositiveSection = false;
    
    for (let i = 0; i < lines.length; i++) {
        // Check if we're entering the positive section
        if (lines[i].match(/positive news summary/i)) {
            inPositiveSection = true;
        }
        
        // Format bullet points based on section
        if (lines[i].match(/^[-•*]\s*(.*?)$/)) {
            if (inPositiveSection) {
                lines[i] = lines[i].replace(/^([-•*]\s*)(.*?)$/, 
                    '<div class="summary-theme">$2</div>');
            } else {
                lines[i] = lines[i].replace(/^([-•*]\s*)(.*?)$/, 
                    '<div class="summary-detail">$2</div>');
            }
        }
    }
    
    formattedSummary = lines.join('\n');
    
    // Convert newlines to <br> tags for proper HTML display
    formattedSummary = formattedSummary.replace(/\n/g, '<br>');
    
    // Clean up any extra <br> tags before headers
    formattedSummary = formattedSummary.replace(/<br><h([34])/g, '<h$1');
    formattedSummary = formattedSummary.replace(/<\/h([34])><br>/g, '</h$1>');
    
    container.innerHTML = formattedSummary;
}

/**
 * Display the sentiment analysis results for a country
 */
function displayCountryResults(data) {
    // Check if we have data
    if (!data || data.error) {
        const errorMessage = data && data.error ? data.error : "No data available";
        document.getElementById('country-results').innerHTML = `
            <div class="alert alert-warning">
                <h3>No Data Available</h3>
                <p>${errorMessage}</p>
            </div>
        `;
        return;
    }

    // Show country details container
    const countryDetails = document.getElementById('country-details');
    if (countryDetails) {
        countryDetails.style.display = 'block';
    }
    
    // Set country name
    const countryName = document.getElementById('country-name');
    if (countryName) {
        countryName.textContent = data.country;
    }

    // Update timestamp
    const timestamp = moment(data.timestamp).format('MMMM D, YYYY h:mm A');
    const lastUpdatedElement = document.getElementById('last-updated');
    if (lastUpdatedElement) {
        lastUpdatedElement.textContent = timestamp;
    }
    
    // Update sentiment meter
    const meanScore = data.mean_score;
    const meanSentimentElement = document.getElementById('mean-sentiment');
    if (meanSentimentElement) {
        meanSentimentElement.textContent = meanScore.toFixed(2);
    }
    
    // Update standard deviation if the element exists
    const stdDevElement = document.getElementById('std-deviation');
    if (stdDevElement && data.std_dev !== undefined) {
        stdDevElement.textContent = data.std_dev.toFixed(2);
    }
    
    // Update the meter classes if element exists
    const sentimentMeterElement = document.getElementById('sentiment-meter-bar');
    if (sentimentMeterElement) {
        updateSentimentMeterClasses(meanScore);
    }
    
    // Update statistics for negative/positive
    const negativeTitle = document.getElementById('negative-title');
    const negativeScore = document.getElementById('negative-score');
    const positiveTitle = document.getElementById('positive-title');
    const positiveScore = document.getElementById('positive-score');
    
    if (negativeTitle) negativeTitle.textContent = data.most_negative_title || "N/A";
    if (negativeScore) negativeScore.textContent = data.most_negative_score ? data.most_negative_score.toFixed(2) : "N/A";
    if (positiveTitle) positiveTitle.textContent = data.most_positive_title || "N/A";
    if (positiveScore) positiveScore.textContent = data.most_positive_score ? data.most_positive_score.toFixed(2) : "N/A";
    
    // Update news summary
    const summaryElement = document.getElementById('news-summary');
    if (summaryElement) {
        formatAndDisplaySummary(data.summary, summaryElement);
    }
    
    // Update articles list
    const articlesContainer = document.getElementById('articles-list');
    if (articlesContainer) {
        articlesContainer.innerHTML = '';
        
        if (data.articles && data.articles.length > 0) {
            data.articles.forEach(article => {
                const sentimentClass = getSentimentClass(article.sentiment_score);
                const card = document.createElement('div');
                card.className = `card mb-3 ${sentimentClass}`;
                
                card.innerHTML = `
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h5 class="card-title">${article.title}</h5>
                            <span class="badge ${getSentimentBadgeClass(article.sentiment_score)}">${article.sentiment_score.toFixed(2)}</span>
                        </div>
                        <p class="card-text">${article.snippet}</p>
                        <a href="${article.link}" target="_blank" class="btn btn-outline-primary btn-sm">Read More</a>
                    </div>
                `;
                articlesContainer.appendChild(card);
            });
        } else {
            articlesContainer.innerHTML = '<p>No articles available</p>';
        }
    }
    
    // Update ACLED data if available
    if (data.acled && data.acled.has_data) {
        displayAcledData(data.acled);
    }
}

/**
 * Helper function to get color based on sentiment score
 */
function getSentimentColor(score) {
    if (score <= -1.5) return "#3D2D4E"; // Extremely negative (deep purple)
    if (score <= -1.0) return "#EA6D8D"; // Very negative (rose pink)
    if (score < 0) return "#A6E4D9";     // Somewhat negative (light teal)
    if (score === 0) return "#F9E062";   // Neutral (yellow)
    if (score <= 1.0) return "#A6E4D9";  // Somewhat positive (light teal)
    if (score <= 1.5) return "#13867A";  // Very positive (teal green)
    return "#000000";                    // Extremely positive (black)
}

/**
 * Helper function to get sentiment class for styling
 */
function getSentimentClass(score) {
    if (score <= -1.5) return "very-negative";
    if (score <= -0.5) return "negative";
    if (score <= 0.5) return "neutral";
    if (score <= 1.5) return "positive";
    return "very-positive";
}

/**
 * Helper function to get badge class for sentiment display
 */
function getSentimentBadgeClass(score) {
    if (score <= -1.5) return "bg-danger";
    if (score <= -0.5) return "bg-danger text-white";
    if (score <= 0.5) return "bg-warning text-dark";
    if (score <= 1.5) return "bg-success text-white";
    return "bg-success";
}

/**
 * Trigger a new analysis for a country
 */
function triggerAnalysis(country) {
    // Show loading state
    document.getElementById('country-details').innerHTML = `
        <h2>${country}</h2>
        <div class="text-center my-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Running sentiment analysis for ${country}...</p>
            <p class="text-muted">This may take a minute or two.</p>
        </div>
    `;
    
    // Call API to trigger analysis
    fetch(`/api/analyze/${country}`, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Reload the country data
            setTimeout(() => {
                selectCountry(country);
            }, 1000);
        } else {
            throw new Error(data.message || 'Analysis failed');
        }
    })
    .catch(error => {
        console.error('Error triggering analysis:', error);
        document.getElementById('country-details').innerHTML = `
            <h2>${country}</h2>
            <div class="alert alert-danger">
                <h3>Analysis Failed</h3>
                <p>${error.message || 'An error occurred while analyzing the news sentiment.'}</p>
                <button class="btn btn-primary" onclick="triggerAnalysis('${country}')">
                    Try Again
                </button>
            </div>
        `;
    });
}
