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
            loadSystemInfo(),
            loadRepositories()
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
        console.log('DEBUG: Loading health status from API...');
        console.log('DEBUG: Health URL:', `${API_BASE_URL}/health`);
        const response = await fetch(`${API_BASE_URL}/health`);
        console.log('DEBUG: Health response status:', response.status);
        console.log('DEBUG: Health response ok:', response.ok);
        
        const data = await response.json();
        console.log('DEBUG: Health data:', data);
        
        updateOverallStatus(data);
        updateServiceStatuses(data.services);
    } catch (error) {
        console.error('DEBUG: Health status error details:', error);
        console.error('Failed to load health status:', error);
        updateOverallStatus({ status: 'unhealthy' });
        showError('Failed to load health status');
    }
}

// Load system information
async function loadSystemInfo() {
    try {
        const response = await fetch('/info');
        const data = await response.json();
        
        updateSystemInfo(data);
    } catch (error) {
        console.error('Failed to load system info:', error);
        showError('Failed to load system information');
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
    
    // Update Hugging Face LLM status
    const huggingfaceLlmElement = document.getElementById('huggingfaceLlmStatus');
    if (huggingfaceLlmElement && services.huggingface_llm) {
        huggingfaceLlmElement.innerHTML = createServiceStatusHTML(services.huggingface_llm, 'Hugging Face LLM');
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

async function testHuggingFaceLLM() {
    await testService('llm', 'Hugging Face LLM');
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

// Tab Navigation Functions
function switchTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabName + 'Content');
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Add active class to selected tab
    const selectedTab = document.getElementById(tabName + 'Tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Load tab-specific data
    if (tabName === 'repositories') {
        loadRepositories();
        loadSummaries();
    }
}

// Repository Management Functions
async function loadRepositories() {
    try {
        console.log('DEBUG: Loading repositories from API...');
        const response = await fetch(`${API_BASE_URL}/repositories`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const responseData = await response.json();
        console.log('DEBUG: Raw API response:', responseData);
        console.log('DEBUG: Response type:', typeof responseData);
        console.log('DEBUG: Is array?', Array.isArray(responseData));
        
        // Extract repositories array from response object
        const repositories = responseData.repositories || responseData;
        console.log('DEBUG: Extracted repositories:', repositories);
        console.log('DEBUG: Repositories type:', typeof repositories);
        console.log('DEBUG: Repositories is array?', Array.isArray(repositories));
        
        updateRepositoryList(repositories);
        updateRepositoryStats(repositories);
    } catch (error) {
        console.error('Failed to load repositories:', error);
        showError('Failed to load repositories from server');
        const listElement = document.getElementById('repositoryList');
        if (listElement) {
            listElement.innerHTML = '<div class="error">Failed to load repositories. Please check if the backend server is running.</div>';
        }
    }
}

async function addRepository() {
    const repoUrl = document.getElementById('repoUrl').value.trim();
    if (!repoUrl) {
        showError('Please enter a repository URL');
        return;
    }
    
    // Validate GitHub URL format
    const githubUrlPattern = /^https:\/\/github\.com\/[\w\-\.]+\/[\w\-\.]+\/?$/;
    if (!githubUrlPattern.test(repoUrl)) {
        showError('Please enter a valid GitHub repository URL');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/repositories`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                github_url: repoUrl
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        showSuccess('Repository added successfully!');
        document.getElementById('repoUrl').value = '';
        loadRepositories();
    } catch (error) {
        console.error('Failed to add repository:', error);
        showError(`Failed to add repository: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function updateRepositoryList(repositories) {
    const listElement = document.getElementById('repositoryList');
    if (!listElement) return;
    
    if (repositories.length === 0) {
        listElement.innerHTML = `
            <div class="info-item">
                <div class="info-label">No repositories found</div>
                <div class="info-value">Add your first repository above</div>
            </div>
        `;
        return;
    }
    
    listElement.innerHTML = repositories.map(repo => `
        <div class="repo-item ${repo.is_active ? 'active' : 'inactive'}">
            <div class="repo-info">
                <h4>${repo.full_name}</h4>
                <p>${repo.description || 'No description available'}</p>
                <div class="repo-stats">
                    <span>⭐ ${repo.stars_count}</span>
                    <span>🍴 ${repo.forks_count}</span>
                    <span>📝 ${repo.language || 'Unknown'}</span>
                    <span>👤 ${repo.owner_login}</span>
                </div>
            </div>
            <div class="repo-actions">
                <button onclick="generateWeeklySummary(${repo.id})"
                        class="btn btn-primary" id="summarize-btn-${repo.id}">
                    <i class="fas fa-file-alt"></i>
                    Summarize
                </button>
                <button onclick="removeRepository(${repo.id})" class="btn btn-danger">
                    <i class="fas fa-trash"></i>
                    Remove
                </button>
            </div>
        </div>
    `).join('');
}

function updateRepositoryStats(repositories) {
    const monitoredCount = repositories.filter(r => r.is_active).length;
    const totalStars = repositories.reduce((sum, r) => sum + r.stars_count, 0);
    
    const monitoredElement = document.getElementById('monitoredCount');
    const starsElement = document.getElementById('totalStars');
    
    if (monitoredElement) monitoredElement.textContent = monitoredCount;
    if (starsElement) starsElement.textContent = totalStars;
    
    // Mock data for other stats
    const recentCommitsElement = document.getElementById('recentCommits');
    const summariesElement = document.getElementById('summariesCount');
    
    if (recentCommitsElement) recentCommitsElement.textContent = Math.floor(Math.random() * 20);
    if (summariesElement) summariesElement.textContent = Math.floor(Math.random() * 10);
}

async function toggleMonitoring(repoId) {
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/repositories/${repoId}/toggle`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        showSuccess('Repository monitoring status updated');
        loadRepositories();
    } catch (error) {
        console.error('Failed to toggle monitoring:', error);
        showError(`Failed to update monitoring status: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

async function removeRepository(repoId) {
    if (!confirm('Are you sure you want to remove this repository from monitoring?')) {
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/repositories/${repoId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        showSuccess('Repository removed successfully');
        loadRepositories();
    } catch (error) {
        console.error('Failed to remove repository:', error);
        showError(`Failed to remove repository: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

// Weekly Summary Generation Functions
async function generateWeeklySummary(repoId) {
    try {
        const button = document.getElementById(`summarize-btn-${repoId}`);
        if (!button) return;
        
        // Update button to loading state
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        button.className = 'btn btn-secondary';
        
        showSuccess('Starting weekly summary generation...');
        
        const response = await fetch(`${API_BASE_URL}/repositories/${repoId}/summaries/generate-weekly`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                summary_type: "weekly"
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Weekly summary generation started:', result);
        
        // Start polling for status
        pollSummaryStatus(repoId);
        
    } catch (error) {
        console.error('Failed to generate weekly summary:', error);
        showError(`Failed to generate weekly summary: ${error.message}`);
        
        // Reset button state
        const button = document.getElementById(`summarize-btn-${repoId}`);
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-file-alt"></i> Summarize';
            button.className = 'btn btn-primary';
        }
    }
}

async function pollSummaryStatus(repoId) {
    const maxAttempts = 60; // Poll for up to 5 minutes (60 * 5 seconds)
    let attempts = 0;
    
    const pollInterval = setInterval(async () => {
        try {
            attempts++;
            
            const response = await fetch(`${API_BASE_URL}/repositories/${repoId}/summaries/weekly-status`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const status = await response.json();
            console.log('Summary status:', status);
            
            const button = document.getElementById(`summarize-btn-${repoId}`);
            
            if (status.status === 'completed') {
                clearInterval(pollInterval);
                
                // Update button to success state
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-check"></i> Completed';
                    button.className = 'btn btn-success';
                    
                    // Reset button after 3 seconds
                    setTimeout(() => {
                        button.innerHTML = '<i class="fas fa-file-alt"></i> Summarize';
                        button.className = 'btn btn-primary';
                    }, 3000);
                }
                
                showSuccess('Weekly summary generated successfully!');
                
                // Refresh summaries list
                loadSummaries();
                
            } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                
                // Update button to error state
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Failed';
                    button.className = 'btn btn-danger';
                    
                    // Reset button after 3 seconds
                    setTimeout(() => {
                        button.innerHTML = '<i class="fas fa-file-alt"></i> Summarize';
                        button.className = 'btn btn-primary';
                    }, 3000);
                }
                
                showError(`Summary generation failed: ${status.message || 'Unknown error'}`);
                
            } else if (status.status === 'in_progress') {
                // Update button with progress message
                if (button && status.message) {
                    const progressMessages = {
                        'fetching_commits': 'Fetching commits...',
                        'generating_summary': 'Generating AI summary...',
                        'saving_summary': 'Saving summary...'
                    };
                    
                    const displayMessage = progressMessages[status.message] || status.message;
                    button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${displayMessage}`;
                }
                
            } else if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
                
                // Timeout - reset button
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-clock"></i> Timeout';
                    button.className = 'btn btn-warning';
                    
                    // Reset button after 3 seconds
                    setTimeout(() => {
                        button.innerHTML = '<i class="fas fa-file-alt"></i> Summarize';
                        button.className = 'btn btn-primary';
                    }, 3000);
                }
                
                showWarning('Summary generation is taking longer than expected. Please try again later.');
            }
            
        } catch (error) {
            console.error('Failed to poll summary status:', error);
            clearInterval(pollInterval);
            
            // Reset button state
            const button = document.getElementById(`summarize-btn-${repoId}`);
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-file-alt"></i> Summarize';
                button.className = 'btn btn-primary';
            }
            
            showError('Failed to check summary generation status');
        }
    }, 5000); // Poll every 5 seconds
}

async function loadSummaries(repositoryId = null) {
    try {
        let allSummaries = [];
        
        if (repositoryId) {
            // Load summaries for a specific repository
            const response = await fetch(`${API_BASE_URL}/repositories/${repositoryId}/summaries`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            allSummaries = await response.json();
        } else {
            // Load summaries for all repositories
            const reposResponse = await fetch(`${API_BASE_URL}/repositories`);
            
            if (!reposResponse.ok) {
                throw new Error(`HTTP error! status: ${reposResponse.status}`);
            }
            
            const responseData = await reposResponse.json();
            console.log('DEBUG loadSummaries: Raw API response:', responseData);
            console.log('DEBUG loadSummaries: Response type:', typeof responseData);
            console.log('DEBUG loadSummaries: Is array?', Array.isArray(responseData));
            
            // Extract repositories array from response object
            const repositories = responseData.repositories || responseData;
            console.log('DEBUG loadSummaries: Extracted repositories:', repositories);
            console.log('DEBUG loadSummaries: Repositories type:', typeof repositories);
            console.log('DEBUG loadSummaries: Repositories is array?', Array.isArray(repositories));
            
            if (!Array.isArray(repositories)) {
                console.error('DEBUG loadSummaries: repositories is not an array!', repositories);
                throw new Error('Invalid response format: repositories is not an array');
            }
            
            // Load summaries for each repository
            const summaryPromises = repositories.map(async (repo) => {
                try {
                    const summariesResponse = await fetch(`${API_BASE_URL}/repositories/${repo.id}/summaries`);
                    if (summariesResponse.ok) {
                        const summaries = await summariesResponse.json();
                        return summaries.map(summary => ({
                            ...summary,
                            repository_name: repo.full_name
                        }));
                    }
                    return [];
                } catch (error) {
                    console.warn(`Failed to load summaries for repository ${repo.full_name}:`, error);
                    return [];
                }
            });
            
            const summaryArrays = await Promise.all(summaryPromises);
            allSummaries = summaryArrays.flat();
        }
        
        updateSummariesList(allSummaries);
    } catch (error) {
        console.error('Failed to load summaries:', error);
        showError('Failed to load summaries from server');
        const summariesElement = document.getElementById('summariesList');
        if (summariesElement) {
            summariesElement.innerHTML = '<div class="error">Failed to load summaries. Please check if the backend server is running.</div>';
        }
    }
}

function updateSummariesList(summaries) {
    const summariesElement = document.getElementById('summariesList');
    if (!summariesElement) return;
    
    if (summaries.length === 0) {
        summariesElement.innerHTML = `
            <div class="info-item">
                <div class="info-label">No summaries available</div>
                <div class="info-value">Summaries will appear here once repositories are analyzed</div>
            </div>
        `;
        return;
    }
    
    summariesElement.innerHTML = summaries.map(summary => `
        <div class="summary-item">
            <div class="summary-header">
                <h4 class="summary-title">${summary.title}</h4>
                <div class="summary-meta">
                    <span>${summary.repository_name}</span> •
                    <span>${new Date(summary.created_at).toLocaleDateString()}</span>
                </div>
            </div>
            <div class="summary-content">
                ${summary.content}
            </div>
            ${summary.tags ? `
                <div class="summary-tags">
                    ${summary.tags.map(tag => `<span class="summary-tag">${tag}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Export functions for global access
window.refreshHealth = refreshHealth;
window.testDatabase = testDatabase;
window.testHuggingFaceLLM = testHuggingFaceLLM;
window.switchTab = switchTab;
window.addRepository = addRepository;
window.toggleMonitoring = toggleMonitoring;
window.removeRepository = removeRepository;
window.generateWeeklySummary = generateWeeklySummary;