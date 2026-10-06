/**
 * CrediGuard Frontend JavaScript
 * Handles real-time DTI calculation, delete confirmation dialogs, and Chart.js graphs.
 */

document.addEventListener('DOMContentLoaded', function () {
    // ----------------------------------------------------
    // 1. Automatic Real-Time Debt-to-Income (DTI) Ratio Calculation
    // ----------------------------------------------------
    const incomeInput = document.getElementById('annual_income');
    const debtInput = document.getElementById('existing_debt');
    const dtiOutput = document.getElementById('dti_display');

    function calculateDTI() {
        if (!incomeInput || !debtInput || !dtiOutput) return;

        const income = parseFloat(incomeInput.value) || 0;
        const debt = parseFloat(debtInput.value) || 0;

        if (income > 0) {
            const dti = ((debt / income) * 100).toFixed(2);
            dtiOutput.value = dti + '%';
            
            // Highlight color based on DTI ratio threshold
            if (dti < 20) {
                dtiOutput.className = 'form-control bg-success-subtle text-success fw-bold';
            } else if (dti <= 35) {
                dtiOutput.className = 'form-control bg-warning-subtle text-warning-emphasis fw-bold';
            } else {
                dtiOutput.className = 'form-control bg-danger-subtle text-danger fw-bold';
            }
        } else {
            dtiOutput.value = '0.00%';
            dtiOutput.className = 'form-control fw-bold';
        }
    }

    if (incomeInput && debtInput) {
        incomeInput.addEventListener('input', calculateDTI);
        debtInput.addEventListener('input', calculateDTI);
        calculateDTI(); // Initial trigger on form load
    }

    // ----------------------------------------------------
    // 2. JavaScript Delete Application Confirmation
    // ----------------------------------------------------
    const deleteForms = document.querySelectorAll('.delete-app-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            const appName = this.getAttribute('data-app-name') || 'this application';
            const confirmed = confirm(`Are you sure you want to delete the application for "${appName}"?\n\nThis action will also permanently delete all associated prediction history.`);
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});

// ----------------------------------------------------
// 3. Chart.js Dashboard Visualizations
// ----------------------------------------------------
function renderDashboardCharts(riskData, empData, featureData) {
    // Risk Doughnut Chart
    const riskCtx = document.getElementById('riskDistributionChart');
    if (riskCtx) {
        new Chart(riskCtx, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                datasets: [{
                    data: [riskData.low, riskData.medium, riskData.high],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    // Employment Status Bar Chart
    const empCtx = document.getElementById('employmentStatusChart');
    if (empCtx) {
        new Chart(empCtx, {
            type: 'bar',
            data: {
                labels: empData.labels,
                datasets: [{
                    label: 'Number of Applicants',
                    data: empData.counts,
                    backgroundColor: '#3b82f6',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, precision: 0 }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // Feature Importance Horizontal Bar Chart
    const featureCtx = document.getElementById('featureImportanceChart');
    if (featureCtx && featureData && featureData.labels) {
        new Chart(featureCtx, {
            type: 'bar',
            data: {
                labels: featureData.labels,
                datasets: [{
                    label: 'Feature Importance Weight',
                    data: featureData.values,
                    backgroundColor: '#6366f1',
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => value + '%'
                        }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: context => ` Importance: ${context.raw.toFixed(1)}%`
                        }
                    }
                }
            }
        });
    }
}

// ----------------------------------------------------
// 4. Chart.js Risk Probability Visualization
// ----------------------------------------------------
function renderPredictionProbabilityChart(lowProb, medProb, highProb) {
    const probCtx = document.getElementById('predictionProbabilityChart');
    if (probCtx) {
        new Chart(probCtx, {
            type: 'bar',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                datasets: [{
                    label: 'Probability (%)',
                    data: [lowProb, medProb, highProb],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y', // Horizontal Bar Chart
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { callback: value => value + '%' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}
