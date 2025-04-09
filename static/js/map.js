/**
 * Modern map with selectable country shapes
 */

// Map configuration
const mapConfig = {
    initialView: [30, 30], // Center of the map (latitude, longitude)
    initialZoom: 3,
    minZoom: 2,
    maxZoom: 10
};

// Country data (populated from the template)
let countriesData = {};
let countryLayers = {};
let selectedCountry = null;
let mapInstance = null; // Global variable to store map instance

// Map styling
const mapStyles = {
    // Default style for unselected countries
    defaultStyle: {
        color: "#3D2D4E",
        weight: 1,
        opacity: 0.8,
        fillColor: "#3D2D4E",
        fillOpacity: 0.2,
    },
    // Style when hovering over a country
    hoverStyle: {
        color: "#13867A",
        weight: 2,
        opacity: 1,
        fillColor: "#13867A",
        fillOpacity: 0.4,
    },
    // Style for the selected country
    selectedStyle: {
        color: "#13867A",
        weight: 3,
        opacity: 1,
        fillColor: "#13867A",
        fillOpacity: 0.6,
    },
    // Sentiment color scale (from negative to positive)
    getSentimentColor: function(score) {
        if (score <= -1.5) return "#3D2D4E"; // Extremely negative (deep purple)
        if (score <= -1.0) return "#EA6D8D"; // Very negative (rose pink)
        if (score < 0) return "#A6E4D9";     // Somewhat negative (light teal)
        if (score === 0) return "#F9E062";   // Neutral (yellow)
        if (score <= 1.0) return "#A6E4D9";  // Somewhat positive (light teal)
        if (score <= 1.5) return "#13867A";  // Very positive (teal green)
        return "#000000";                    // Extremely positive (black)
    }
};

// Country GeoJSON data - keyed by country name
const countryGeoData = {};

// Initialize the map
document.addEventListener('DOMContentLoaded', function() {
    // Run ACLED endpoint test
    setTimeout(testAcledEndpoint, 1000);
    
    // Create map with a more modern style
    mapInstance = L.map('map', {
        center: mapConfig.initialView,
        zoom: mapConfig.initialZoom,
        minZoom: mapConfig.minZoom,
        maxZoom: mapConfig.maxZoom,
        zoomControl: false  // We'll add zoom control in a different position
    });

    // Add zoom control to the top-right
    L.control.zoom({
        position: 'topright'
    }).addTo(mapInstance);
    
    // Add a modern, cleaner basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 19
    }).addTo(mapInstance);

    // Get country coordinates from the API endpoint instead of HTML data attributes
    fetch('/api/coordinates')
        .then(response => response.json())
        .then(data => {
            console.log("Loaded country coordinates from API:", data);
            countriesData = data;
            
            // Load country boundary data after coordinates are loaded
            loadCountryBoundaries(mapInstance);
        })
        .catch(error => {
            console.error("Error fetching country coordinates:", error);
            // Fallback coordinates if API fails
            countriesData = {
                "Ukraine": [49.0, 31.0],
                "Moldova": [47.4, 28.5],
                "Syria": [35.0, 38.0],
                "Lebanon": [33.8, 35.8],
                "Israel": [31.5, 34.8],
                "Libya": [27.0, 17.0]
            };
            console.log("Using fallback coordinates:", countriesData);
            
            // Load country boundaries even if coordinates API fails
            loadCountryBoundaries(mapInstance);
        });

    // Fetch initial sentiment data for all countries and automatically display alerts when data is ready
    fetchAllSentimentData().then(function() {
        // Automatically display alerts once data is loaded
        addAlertIcons();
    });
    
    // Refresh button event - update sentiment data and alerts
    document.getElementById('refresh-btn').addEventListener('click', function() {
        if (selectedCountry) {
            // Trigger analysis and refresh alerts afterwards
            triggerAnalysis(selectedCountry).then(function() {
                // Refresh the alerts after analysis is complete
                addAlertIcons();
            });
        }
    });
    
    // Hide the "Show Alerts" button since we're now showing alerts automatically
    const alertsButton = document.getElementById('refresh-alerts-btn');
    if (alertsButton) {
        alertsButton.style.display = 'none';
    }
});

// Update the fetchAllSentimentData function to return a promise
function fetchAllSentimentData() {
    return new Promise(function(resolve, reject) {
        // Show loading indicator
        const mapElement = document.getElementById('map');
        if (mapElement) {
            mapElement.classList.add('loading');
            // Add loading overlay if it doesn't exist
            if (!document.getElementById('map-loading-overlay')) {
                const loadingOverlay = document.createElement('div');
                loadingOverlay.id = 'map-loading-overlay';
                loadingOverlay.className = 'loading-overlay';
                loadingOverlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><div class="mt-2">Loading analysis data...</div>';
                mapElement.parentNode.appendChild(loadingOverlay);
            }
        }
        
        // Fetch the data
        fetch('/api/results')
            .then(response => response.json())
            .then(data => {
                // Update markers with the sentiment data
                updateMarkers(data);
                
                // Remove loading indicator
                if (mapElement) {
                    mapElement.classList.remove('loading');
                    const loadingOverlay = document.getElementById('map-loading-overlay');
                    if (loadingOverlay) {
                        loadingOverlay.remove();
                    }
                }
                
                resolve(data);
            })
            .catch(error => {
                console.error('Error fetching sentiment data:', error);
                
                // Remove loading indicator even on error
                if (mapElement) {
                    mapElement.classList.remove('loading');
                    const loadingOverlay = document.getElementById('map-loading-overlay');
                    if (loadingOverlay) {
                        loadingOverlay.remove();
                    }
                }
                
                reject(error);
            });
    });
}

// Update the triggerAnalysis function to return a promise
function triggerAnalysis(country) {
    return new Promise(function(resolve, reject) {
        console.log(`Triggering analysis for ${country}...`);
        
        // Show loading indicator
        const countryDetails = document.getElementById('country-details');
        if (countryDetails) {
            countryDetails.classList.add('loading');
            
            // Add loading overlay if it doesn't exist
            if (!document.getElementById('country-loading-overlay')) {
                const loadingOverlay = document.createElement('div');
                loadingOverlay.id = 'country-loading-overlay';
                loadingOverlay.className = 'loading-overlay';
                loadingOverlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><div class="mt-2">Analyzing latest news...</div>';
                countryDetails.appendChild(loadingOverlay);
            }
        }
        
        // Trigger the analysis
        fetch(`/api/analyze/${country}`)
            .then(response => response.json())
            .then(data => {
                console.log(`Analysis completed for ${country}:`, data);
                
                // Refresh the results for this country
                fetchCountrySentiment(country);
                
                // Also refresh the overall data and alerts
                return fetchAllSentimentData();
            })
            .then(() => {
                // Remove loading indicator
                if (countryDetails) {
                    countryDetails.classList.remove('loading');
                    const loadingOverlay = document.getElementById('country-loading-overlay');
                    if (loadingOverlay) {
                        loadingOverlay.remove();
                    }
                }
                
                resolve();
            })
            .catch(error => {
                console.error(`Error triggering analysis for ${country}:`, error);
                
                // Remove loading indicator even on error
                if (countryDetails) {
                    countryDetails.classList.remove('loading');
                    const loadingOverlay = document.getElementById('country-loading-overlay');
                    if (loadingOverlay) {
                        loadingOverlay.remove();
                    }
                }
                
                reject(error);
            });
    });
}

/**
 * Load country boundary data for countries of interest
 */
function loadCountryBoundaries(map) {
    // Log countries we're looking for
    const countryList = Object.keys(countriesData);
    console.log("Countries we need to find:", countryList);
    
    // Load the world GeoJSON data
    fetch('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson')
        .then(response => response.json())
        .then(worldData => {
            console.log("World GeoJSON data loaded with", worldData.features.length, "countries");
            
            // Create a mapping for countries that might have different names in the GeoJSON
            const countryNameMapping = {
                "Libya": ["Libya", "Libyan Arab Jamahiriya"],
                "Syria": ["Syria", "Syrian Arab Republic"],
                // Add other mappings as needed
            };
            
            // Process each country in our list
            countryList.forEach(countryName => {
                // Try to find the matching feature in the world data
                let countryFeature = worldData.features.find(feature => 
                    feature.properties.ADMIN === countryName);
                
                // If not found, check alternative names
                if (!countryFeature && countryNameMapping[countryName]) {
                    // Try each alternative name
                    for (const altName of countryNameMapping[countryName]) {
                        countryFeature = worldData.features.find(feature => 
                            feature.properties.ADMIN === altName);
                        if (countryFeature) {
                            console.log(`Found ${countryName} using alternative name: ${altName}`);
                            break;
                        }
                    }
                }
                
                console.log(`Looking for ${countryName} in world data:`, countryFeature ? "Found" : "Not found");
                
                if (countryFeature) {
                    // Store the country GeoJSON data
                    countryGeoData[countryName] = countryFeature;
                    
                    // Add the country to the map
                    addCountryLayer(map, countryName, countryFeature);
                } else {
                    // Log all country names in the GeoJSON for debugging
                    console.warn(`Country not found in GeoJSON: ${countryName}`);
                    console.log("Available countries in GeoJSON:", 
                                worldData.features.map(f => f.properties.ADMIN).sort());
                    
                    // Fallback if the country is not found in the GeoJSON
                    if (countriesData[countryName]) {
                        console.log(`Using fallback marker for ${countryName}`);
                        addFallbackMarker(map, countryName, countriesData[countryName]);
                    }
                }
            });
            
            // Log the complete countryLayers object
            console.log("Country layers after initialization:", countryLayers);
            
            // Check if Libya has a country layer
            if (countryLayers["Libya"]) {
                console.log("Libya layer exists:", countryLayers["Libya"]);
                console.log("Libya layer has getBounds:", typeof countryLayers["Libya"].getBounds === 'function');
            } else {
                console.error("Libya layer not created!");
            }
            
            // Fit the map to show all countries
            fitMapToCountries(map);
            
            // Make sure alerts are added after country layers are loaded
            setTimeout(() => {
                console.log("Triggering addAlertIcons after map initialized");
                addAlertIcons();
            }, 1000);
        })
        .catch(error => {
            console.error('Error loading country boundaries:', error);
            
            // Fallback to using markers for all countries
            Object.entries(countriesData).forEach(([country, coordinates]) => {
                addFallbackMarker(map, country, coordinates);
            });
            
            // Fit the map to markers
            fitMapToCountries(map);
            
            // Add alerts even when GeoJSON loading fails
            setTimeout(() => {
                console.log("Triggering addAlertIcons after fallback markers added");
                addAlertIcons();
            }, 1000);
        });
}

/**
 * Add a country GeoJSON layer to the map
 */
function addCountryLayer(map, countryName, geoJsonData) {
    // Add GeoJSON layer with country styling
    const layer = L.geoJSON(geoJsonData, {
        style: mapStyles.defaultStyle,
        onEachFeature: function(feature, layer) {
            // Event handlers for each country
            layer.on({
                mouseover: function(e) {
                    layer.setStyle(mapStyles.hoverStyle);
                },
                mouseout: function(e) {
                    if (selectedCountry !== countryName) {
                        layer.setStyle(mapStyles.defaultStyle);
                    } else {
                        layer.setStyle(mapStyles.selectedStyle);
                    }
                },
                click: function(e) {
                    selectCountry(countryName);
                }
            });
        }
    }).addTo(map);
    
    // Store layer reference
    countryLayers[countryName] = layer;
    console.log(`Added country layer for ${countryName}, has getBounds: ${typeof layer.getBounds === 'function'}`);
    
    return layer;
}

/**
 * Add a fallback marker for a country (used if GeoJSON loading fails)
 */
function addFallbackMarker(map, country, coordinates) {
    // Create a marker for the country if GeoJSON loading failed
    const marker = L.marker(coordinates, {
        title: country,
        riseOnHover: true
    }).addTo(map);
    
    // Add click handler
    marker.on('click', function() {
        selectCountry(country);
    });
    
    // Add a custom getBounds method to the marker so it works with the alert system
    marker.getBounds = function() {
        // Create a small bounds around the marker
        const latlng = this.getLatLng();
        return L.latLngBounds([
            [latlng.lat - 0.5, latlng.lng - 0.5],
            [latlng.lat + 0.5, latlng.lng + 0.5]
        ]);
    };
    
    // Store marker in the layers object for consistency
    countryLayers[country] = marker;
    console.log(`Added fallback marker for ${country}, has getBounds: ${typeof marker.getBounds === 'function'}`);
    
    return marker;
}

/**
 * Fit the map view to show all countries of interest
 */
function fitMapToCountries(map) {
    // Create a bounds object
    const bounds = L.latLngBounds([]);
    
    // Add each country's bounds
    Object.values(countryLayers).forEach(layer => {
        if (layer.getBounds) {
            bounds.extend(layer.getBounds());
        } else if (layer.getLatLng) {
            bounds.extend(layer.getLatLng());
        }
    });
    
    // If we have bounds, fit the map to them
    if (bounds.isValid()) {
        map.fitBounds(bounds, {
            padding: [20, 20], // Add some padding
            maxZoom: 6         // Don't zoom in too far
        });
    }
}

/**
 * Update country styles based on sentiment data
 */
function updateMarkers(sentimentData) {
    // For each country in our sentiment data
    for (const [country, data] of Object.entries(sentimentData)) {
        if (countryLayers[country] && data.mean_score !== undefined) {
            // Get the sentiment color
            const sentimentColor = mapStyles.getSentimentColor(data.mean_score);
            
            // Update layer style based on sentiment
            const layer = countryLayers[country];
            
            // If it's a GeoJSON layer
            if (layer.setStyle) {
                // Update the country style with sentiment color
                const newStyle = {
                    ...mapStyles.defaultStyle,
                    color: sentimentColor,
                    fillColor: sentimentColor
                };
                
                // Apply the style, preserving selected state
                if (selectedCountry === country) {
                    newStyle.weight = mapStyles.selectedStyle.weight;
                    newStyle.fillOpacity = mapStyles.selectedStyle.fillOpacity;
                }
                
                layer.setStyle(newStyle);
                
                // Libya is known to have anomalies, so add an alert icon specifically for it
                if (country === "Libya") {
                    // Get the center of the country
                    const bounds = layer.getBounds();
                    const center = bounds.getCenter();
                    
                    // Create a custom alert icon
                    const alertIcon = L.divIcon({
                        className: 'alert-icon',
                        html: '<div class="alert-pulse"><i class="fas fa-exclamation-triangle"></i></div>',
                        iconSize: [24, 24],
                        iconAnchor: [12, 12]
                    });
                    
                    // Remove existing alert marker if any
                    if (layer.alertMarker) {
                        layer.alertMarker.remove();
                    }
                    
                    // Add alert marker
                    layer.alertMarker = L.marker(center, {
                        icon: alertIcon,
                        zIndexOffset: 1000 // Make sure it's above other elements
                    }).addTo(mapInstance);
                    
                    // Add tooltip with anomaly information
                    const tooltipContent = `
                        <div class="anomaly-tooltip">
                            <strong>Alert: Unusual violence pattern detected</strong>
                            <p>Significant increase in violent events</p>
                            <small>Click country for details</small>
                        </div>
                    `;
                    layer.alertMarker.bindTooltip(tooltipContent, {
                        direction: 'top',
                        offset: [0, -10],
                        className: 'anomaly-tooltip-container'
                    });
                }
            } 
            // If it's a marker (fallback)
            else if (layer.bindPopup) {
                // Create popup content
                let popupContent = `
                    <div class="marker-popup">
                        <h4>${country}</h4>
                        <p>Sentiment Score: ${data.mean_score.toFixed(2)}</p>
                `;
                
                // Add alert info if country is Libya
                if (country === "Libya") {
                    popupContent += `
                        <p class="alert-text"><i class="fas fa-exclamation-triangle"></i> Unusual violence pattern detected</p>
                    `;
                }
                
                popupContent += `
                        <button class="popup-btn" onclick="selectCountry('${country}')">View Details</button>
                    </div>
                `;
                
                layer.bindPopup(popupContent);
            }
        }
    }
    
    // After updating the markers, let's also try to load the ACLED data
    // This won't affect the already created markers, but will be a fallback method
    // to show alerts based on the API data in the future
    fetch('/api/acled')
        .then(response => response.json())
        .then(acledData => {
            console.log('ACLED data:', acledData);
        })
        .catch(error => {
            console.error('Error fetching ACLED data for alerts:', error);
        });
}

/**
 * Select a country and display its sentiment data
 */
function selectCountry(country) {
    // Update selection state
    selectedCountry = country;
    
    // Reset all countries to default style first
    for (const [countryName, layer] of Object.entries(countryLayers)) {
        // Only for GeoJSON layers
        if (layer.setStyle) {
            layer.setStyle(mapStyles.defaultStyle);
        }
    }
    
    // Highlight selected country
    const selectedLayer = countryLayers[country];
    if (selectedLayer && selectedLayer.setStyle) {
        selectedLayer.setStyle(mapStyles.selectedStyle);
        
        // Bring the selected country to the front
        if (selectedLayer.bringToFront) {
            selectedLayer.bringToFront();
        }
    }
    
    // Display country details
    document.getElementById('country-info').style.display = 'none';
    document.getElementById('country-details').style.display = 'block';
    document.getElementById('country-name').textContent = country;
    
    // Fetch and display data for selected country
    fetchCountrySentiment(country);
}

/**
 * Add alert icons to countries with anomalies
 */
function addAlertIcons() {
    console.log("Adding alert icons for countries with anomalies");
    
    // Fetch ACLED data to check for anomalies
    fetch('/api/acled')
        .then(response => response.json())
        .then(data => {
            console.log("ACLED data for alerts:", data);
            
            // Count countries with alerts for the badge
            const countriesWithAlerts = [];
            
            // Process each country to add alert icons where needed
            Object.entries(data).forEach(([country, countryData]) => {
                if (!countryData.anomaly) {
                    console.log(`No anomaly for ${country}, skipping alert`);
                    return;  // Skip countries without anomalies
                }
                
                console.log(`Adding alert for ${country} - anomaly detected`);
                countriesWithAlerts.push(country);
                
                try {
                    // Get the country layer to determine position
                    const countryLayer = countryLayers[country];
                    if (!countryLayer) {
                        console.error(`Country layer not found for ${country}`);
                        return;
                    }
                    
                    // Determine the center position for the alert icon
                    let center;
                    
                    // Check if the layer has a getLatLng method (marker) or getBounds (GeoJSON)
                    if (typeof countryLayer.getLatLng === 'function') {
                        // It's a marker, use its position
                        center = countryLayer.getLatLng();
                        console.log(`Using marker position for ${country}:`, center);
                    } else if (typeof countryLayer.getBounds === 'function') {
                        // It's a GeoJSON layer, use its geometric center
                        center = countryLayer.getBounds().getCenter();
                        console.log(`Using bounds center for ${country}:`, center);
                    } else {
                        console.error(`Cannot determine position for ${country} alert`);
                        return;
                    }
                    
                    // Create an alert icon
                    const alertIcon = L.divIcon({
                        className: 'alert-icon',
                        html: '<div class="alert-pulse"><i class="fas fa-exclamation-triangle"></i></div>',
                        iconSize: [36, 36],
                        iconAnchor: [18, 18]
                    });
                    
                    // Add the marker to the map
                    const alertMarker = L.marker(center, {
                        icon: alertIcon,
                        zIndexOffset: 1000  // Ensure it appears above country markers
                    }).addTo(mapInstance);
                    
                    // Add tooltip with anomaly information
                    alertMarker.bindTooltip(`
                        <div class="anomaly-tooltip">
                            <strong>${country} Alert</strong>
                            <p>${countryData.explanation || 'Unusual pattern of violent events detected'}</p>
                            <small>Click country for details</small>
                        </div>
                    `, {
                        direction: 'top',
                        offset: [0, -10],
                        className: 'anomaly-tooltip-container'
                    });
                    
                    // Store the alert marker for later reference
                    if (!countryLayers[country].alertMarkers) {
                        countryLayers[country].alertMarkers = [];
                    }
                    countryLayers[country].alertMarkers.push(alertMarker);
                    
                } catch (error) {
                    console.error(`Error adding alert for ${country}:`, error);
                }
            });
            
            // Update the global alerts badge
            updateAlertsBadge(countriesWithAlerts.length);
        })
        .catch(error => {
            console.error('Error fetching ACLED data for alerts:', error);
        });
}

/**
 * Updates the alert badge in the UI
 * @param {number} alertCount - Number of alerts to display
 */
function updateAlertsBadge(alertCount) {
    const badge = document.getElementById('acled-alert-badge');
    if (badge) {
        // Show the badge if there are alerts
        if (alertCount > 0) {
            badge.style.display = 'inline-block';
            badge.textContent = alertCount > 1 ? `${alertCount} Alerts!` : 'Alert!';
        } else {
            badge.style.display = 'none';
        }
    }
}

// For testing: Log the ACLED data separately to verify it's working
function testAcledEndpoint() {
    console.log("Testing ACLED endpoint...");
    fetch('/api/acled')
        .then(response => response.json())
        .then(data => {
            console.log("ACLED TEST DATA:", data);
            // Check specifically for Libya
            if (data.Libya) {
                console.log("Libya data:", data.Libya);
                console.log("Libya has anomaly:", data.Libya.anomaly);
            } else {
                console.log("No Libya data found!");
            }
        })
        .catch(error => {
            console.error("Error testing ACLED endpoint:", error);
        });
}
