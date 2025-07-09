// GitHub Repository Monitor Frontend JavaScript

// Global variables
let healthCheckInterval;
const API_BASE_URL = '/api/v1';

// DOM elements
const statusIndicator = document.getElementById('statusIndicator');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('GitHub Repository Monitor initialized');
    initializeApp();
});

// Initialize application
async function initializeApp() {
    try {
        showLoading(true);
        
        // Load initial data
        await Promise.all([
            loadAppInfo(),
            loadHealthStatus(),
            loadSystemInfo()
        ]);
        
        // Start periodic health checks
        startHealthCheckInterval();
        
        showLoading(false);
    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError('Failed to initialize application');
        showLoading(false);
    }
}

// Show/hide loading overlay
function showLoading(show) {
    if (loadingOverlay) {
        loadingOverlay.classList.toggle('show', show);
    }
}

// Load application information
async function loadAppInfo() {
    try {
        const response = await fetch('/info');
        const data = await response.json();
        
        updateApiInfo(data);
        updateSystemInfo(data);
    } catch (error) {
        console.error('Failed to load app info:', error);
        showError('Failed to load application information');
    }
}

// Load health status
async function loadHealthStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        updateOverallStatus(data);
        updateServiceStatuses(data.services);
    } catch (error) {
        console.error('Failed to load health status:', error);
        updateOverallStatus({ status: 'unhealthy' });
        showError('Failed to load health status');
    }
}

// Update overall status indicator
function updateOverallStatus(healthData) {
    const status = healthData.status || 'unhealthy';
    
    if (statusDot) {
        statusDot.className = `status-dot ${status}`;
    }
    
    if (statusText) {
        const statusMessages = {
            healthy: 'All Systems Operational',
            degraded: 'Some Issues Detected',
            unhealthy: 'System Issues'
        };
        statusText.textContent = statusMessages[status] || 'Unknown Status';
    }
    
    // Update health status card
    const healthStatusElement = document.getElementById('healthStatus');
    if (healthStatusElement) {
        healthStatusElement.innerHTML = createHealthStatusHTML(healthData);
    }
}

// Create health status HTML
function createHealthStatusHTML(healthData) {
    const uptime = healthData.uptime ? formatUptime(healthData.uptime) : 'Unknown';
    const timestamp = healthData.timestamp ? new Date(healthData.timestamp).toLocaleString() : 'Unknown';
    
    return `
        <div class="status-item ${healthData.status || 'unhealthy'}">
            <div class="status-label">Overall Status</div>
            <div class="status-badge ${healthData.status || 'unhealthy'}">${healthData.status || 'Unknown'}</div>
        </div>
        <div class="status-item">
            <div class="status-label">Uptime</div>
            <div class="status-value">${uptime}</div>
        </div>
        <div class="status-item">
            <div class="status-label">Last Check</div>
            <div class="status-value">${timestamp}</div>
        </div>
        <div class="status-item">
            <div class="status-label">Version</div>
            <div class="status-value">${healthData.version || 'Unknown'}</div>
        </div>
    `;
}

// Update individual service statuses
function updateServiceStatuses(services) {
    if (!services) return;
    
    // Update database status
    const databaseElement = document.getElementById('databaseStatus');
    if (databaseElement && services.database) {
        databaseElement.innerHTML = createServiceStatusHTML(services.database, 'Database');
    }
    
    // Update Redis status
    const redisElement = document.getElementById('redisStatus');
    if (redisElement && services.redis) {
        redisElement.innerHTML = createServiceStatusHTML(services.redis, 'Redis');
    }
    
    // Update Ollama status
    const ollamaElement = document.getElementById('ollamaStatus');
    if (ollamaElement && services.ollama) {
        ollamaElement.innerHTML = createServiceStatusHTML(services.ollama, 'Ollama');
    }
}

// Create service status HTML
function createServiceStatusHTML(serviceData, serviceName) {
    const responseTime = serviceData.response_time ? `${serviceData.response_time.toFixed(2)}ms` : 'Unknown';
    
    let detailsHTML = '';
    if (serviceData.details) {
        detailsHTML = Object.entries(serviceData.details)
            .map(([key, value]) => `
                <div class="status-item">
                    <div class="status-label">${formatLabel(key)}</div>
                    <div class="status-value">${formatValue(value)}</div>
                </div>
            `).join('');
    }
    
    return `
        <div class="status-item ${serviceData.status}">
            <div class="status-label">Status</div>
            <div class="status-badge ${serviceData.status}">${serviceData.status}</div>
        </div>
        <div class="status-item">
            <div class="status-label">Response Time</div>
            <div class="status-value">${responseTime}</div>
        </div>
        ${detailsHTML}
    `;
}

// Update API information
function updateApiInfo(appData) {
    const apiInfoElement = document.getElementById('apiInfo');
    if (apiInfoElement) {
        apiInfoElement.innerHTML = `
            <div class="info-item">
                <div class="info-label">Application</div>
                <div class="info-value">${appData.name || 'Unknown'}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Version</div>
                <div class="info-value">${appData.version || 'Unknown'}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Environment</div>
                <div class="info-value">${appData.environment || 'Unknown'}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Debug Mode</div>
                <div class="info-value">${appData.debug ? 'Enabled' : 'Disabled'}</div>
            </div>
        `;
    }
}

// Update system information
function updateSystemInfo(appData) {
    const systemInfoElement = document.getElementById('systemInfo');
    if (systemInfoElement) {
        const currentTime = new Date().toLocaleString();
        
        systemInfoElement.innerHTML = `
            <div class="info-item">
                <div class="info-label">Current Time</div>
                <div class="info-value">${currentTime}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Application Name</div>
                <div class="info-value">${appData.name || 'GitHub Repository Monitor'}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Version</div>
                <div class="info-value">${appData.version || '1.0.0'}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Environment</div>
                <div class="info-value">${appData.environment || 'Development'}</div>
            </div>
        `;
    }
}

// Start periodic health checks
function startHealthCheckInterval() {
    // Clear existing interval
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
    
    // Start new interval (check every 30 seconds)
    healthCheckInterval = setInterval(loadHealthStatus, 30000);
}

// Stop health check interval
function stopHealthCheckInterval() {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }
}

// Refresh health status manually
async function refreshHealth() {
    try {
        showLoading(true);
        await loadHealthStatus();
        showSuccess('Health status refreshed successfully');
    } catch (error) {
        console.error('Failed to refresh health status:', error);
        showError('Failed to refresh health status');
    } finally {
        showLoading(false);
    }
}

// Test individual services
async function testDatabase() {
    await testService('database', 'Database');
}

async function testRedis() {
    await testService('redis', 'Redis');
}

async function testOllama() {
    await testService('ollama', 'Ollama');
}

// Generic service test function
async function testService(serviceName, displayName) {
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE_URL}/health/${serviceName}`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            showSuccess(`${displayName} connection test successful`);
        } else {
            showWarning(`${displayName} connection test failed: ${data.details?.error || 'Unknown error'}`);
        }
        
        // Refresh the specific service status
        const serviceElement = document.getElementById(`${serviceName}Status`);
        if (serviceElement) {
            serviceElement.innerHTML = createServiceStatusHTML(data, displayName);
        }
    } catch (error) {
        console.error(`Failed to test ${serviceName}:`, error);
        showError(`Failed to test ${displayName} connection`);
    } finally {
        showLoading(false);
    }
}

// Utility functions
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
        return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

function formatLabel(key) {
    return key.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function formatValue(value) {
    if (typeof value === 'object' && value !== null) {
        return JSON.stringify(value);
    }
    return String(value);
}

// Notification functions
function showError(message) {
    showNotification(message, 'error');
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showWarning(message) {
    showNotification(message, 'warning');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add styles for notifications
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        z-index: 1001;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    // Set background color based on type
    const colors = {
        error: '#dc3545',
        success: '#28a745',
        warning: '#ffc107',
        info: '#17a2b8'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Add CSS for notifications animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .notification-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 15px;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: white;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .notification-close:hover {
        opacity: 0.8;
    }
`;
document.head.appendChild(style);

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopHealthCheckInterval();
    } else {
        startHealthCheckInterval();
        loadHealthStatus(); // Refresh immediately when page becomes visible
    }
});

// Handle window beforeunload
window.addEventListener('beforeunload', function() {
    stopHealthCheckInterval();
});

// Export functions for global access
window.refreshHealth = refreshHealth;
window.testDatabase = testDatabase;
window.testRedis = testRedis;
window.testOllama = testOllama;