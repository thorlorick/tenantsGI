// Simplified shared utilities for Grade Insight
class GradeUtils {
    static escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    static formatDate(dateString) {
        if (!dateString) return 'No date';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    static isValidEmail(email) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailPattern.test(email);
    }

    static getGradeClass(percentage) {
        if (percentage >= 80) return 'grade-good';
        if (percentage >= 60) return 'grade-medium';
        return 'grade-poor';
    }

    static calculatePercentage(score, maxPoints) {
        return maxPoints > 0 ? Math.round((score / maxPoints) * 100) : 0;
    }

    static async fetchWithErrorHandling(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    static showError(containerId, message) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="error">
                <strong>Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
        container.style.display = 'block';
    }
}

// Simple grades table
class GradesTable {
    constructor() {
        this.students = [];
        this.assignments = [];
        this.init();
    }

    init() {
        this.loadGrades();
    }

    async loadGrades() {
        try {
            const data = await GradeUtils.fetchWithErrorHandling('/api/grades-table');
            this.students = data.students || [];
            this.extractAssignments();
            this.renderTable();
        } catch (error) {
            console.error('Error loading grades:', error);
            GradeUtils.showError('tableBody', 'Failed to load grades. Please refresh the page.');
        }
    }

    extractAssignments() {
        const assignmentMap = new Map();
        this.students.forEach(student => {
            student.grades.forEach(grade => {
                const key = `${grade.assignment}|${grade.date}`;
                if (!assignmentMap.has(key)) {
                    assignmentMap.set(key, {
                        name: grade.assignment,
                        date: grade.date,
                        max_points: grade.max_points
                    });
                }
            });
        });
        this.assignments = Array.from(assignmentMap.values());
        this.assignments.sort((a, b) => {
            if (a.date && b.date) return new Date(a.date) - new Date(b.date);
            return a.name.localeCompare(b.name);
        });
    }

    renderTable() {
        this.renderHeader();
        this.renderBody();
    }

    renderHeader() {
        const headerRow = document.getElementById('tableHeader');
        headerRow.innerHTML = '<th>Student</th>';
        
        this.assignments.forEach(assignment => {
            const th = document.createElement('th');
            th.innerHTML = `
                <div class="assignment-name">${GradeUtils.escapeHtml(assignment.name)}</div>
                <div class="assignment-info">
                    ${assignment.date ? GradeUtils.formatDate(assignment.date) : 'No date'} | 
                    ${assignment.max_points} pts
                </div>
            `;
            headerRow.appendChild(th);
        });
    }

    renderBody() {
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';
        
        if (this.students.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" class="no-results">No students found.</td></tr>';
            return;
        }

        this.students.forEach(student => {
            const row = this.createStudentRow(student);
            tbody.appendChild(row);
        });
    }

    createStudentRow(student) {
        const row = document.createElement('tr');
        
        // Student info cell
        const studentCell = document.createElement('td');
        studentCell.innerHTML = `
            <div class="student-name">${GradeUtils.escapeHtml(`${student.last_name}, ${student.first_name}`)}</div>
            <div class="student-email">${GradeUtils.escapeHtml(student.email)}</div>
        `;
        row.appendChild(studentCell);

        // Grade cells
        this.assignments.forEach(assignment => {
            const gradeCell = this.createGradeCell(student, assignment);
            row.appendChild(gradeCell);
        });

        return row;
    }

    createGradeCell(student, assignment) {
        const gradeCell = document.createElement('td');
        gradeCell.className = 'grade-cell';
        const grade = student.grades.find(g => g.assignment === assignment.name && g.date === assignment.date);
        
        if (grade) {
            const percentage = GradeUtils.calculatePercentage(grade.score, grade.max_points);
            const gradeClass = GradeUtils.getGradeClass(percentage);
            gradeCell.innerHTML = `
                <div class="grade-score ${gradeClass}">${grade.score}/${grade.max_points}</div>
                <div class="grade-percentage">${percentage}%</div>
            `;
        } else {
            gradeCell.innerHTML = '<div class="no-grade">—</div>';
        }
        
        return gradeCell;
    }
}

// Simple student portal
class StudentPortal {
    constructor() {
        this.emailInput = document.getElementById('emailInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.resultsSection = document.getElementById('resultsSection');
        this.init();
    }

    init() {
        this.bindEvents();
        this.handleURLParams();
    }

    bindEvents() {
        this.searchBtn.addEventListener('click', () => this.searchGrades());
        this.clearBtn.addEventListener('click', () => this.clearResults());
        
        this.emailInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchGrades();
        });
    }

    handleURLParams() {
        const params = new URLSearchParams(window.location.search);
        const emailFromURL = params.get('email');
        if (emailFromURL) {
            this.emailInput.value = decodeURIComponent(emailFromURL);
            this.searchGrades();
        }
    }

    clearResults() {
        this.resultsSection.style.display = 'none';
        this.clearBtn.style.display = 'none';
        this.emailInput.value = '';
        this.emailInput.focus();
    }

    async searchGrades() {
        const email = this.emailInput.value.trim();
        
        if (!email) {
            this.showError('Please enter your email address.');
            return;
        }

        if (!GradeUtils.isValidEmail(email)) {
            this.showError('Please enter a valid email address.');
            return;
        }

        try {
            this.showLoading();
            this.searchBtn.disabled = true;
            this.clearBtn.style.display = 'inline-block';
            
            const response = await fetch(`/api/student/${encodeURIComponent(email)}/grades`);
            
            if (response.status === 404) {
                this.showNotFound(email);
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const studentData = await response.json();
            this.displayStudentGrades(studentData);
            
        } catch (error) {
            console.error('Error fetching student grades:', error);
            this.showError('Unable to fetch grades. Please try again later.');
        } finally {
            this.searchBtn.disabled = false;
        }
    }

    displayStudentGrades(student) {
        const overallPercentage = student.overall_percentage || 0;
        const gradeClass = GradeUtils.getGradeClass(overallPercentage);
        
        const gradesTableHtml = student.grades && student.grades.length > 0 
            ? this.generateGradesTable(student.grades)
            : '<p class="no-data">No assignments found.</p>';

        this.resultsSection.innerHTML = `
            <div class="student-header">
                <div class="student-name">${GradeUtils.escapeHtml(student.first_name)} ${GradeUtils.escapeHtml(student.last_name)}</div>
                <div class="student-email">${GradeUtils.escapeHtml(student.email)}</div>
                
                <div class="overall-stats">
                    <div class="stat-box">
                        <span class="stat-value">${student.total_assignments || 0}</span>
                        <div class="stat-label">Total Assignments</div>
                    </div>
                    <div class="stat-box">
                        <span class="stat-value">${student.total_points || 0}</span>
                        <div class="stat-label">Points Earned</div>
                    </div>
                    <div class="stat-box">
                        <span class="stat-value">${student.max_possible || 0}</span>
                        <div class="stat-label">Points Possible</div>
                    </div>
                </div>
                
                <div class="overall-grade ${gradeClass}">
                    Overall Grade: ${overallPercentage.toFixed(1)}%
                </div>
            </div>
            
            <div class="grades-table-container">
                ${gradesTableHtml}
            </div>
        `;

        this.resultsSection.style.display = 'block';
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    generateGradesTable(grades) {
        const tableRows = grades.map(grade => {
            const percentage = GradeUtils.calculatePercentage(grade.score, grade.max_points);
            const gradeClass = GradeUtils.getGradeClass(percentage);
            const date = grade.date ? GradeUtils.formatDate(grade.date) : 'No date';
            
            return `
                <tr>
                    <td>
                        <div class="assignment-name">${GradeUtils.escapeHtml(grade.assignment)}</div>
                        <div class="assignment-date">${date}</div>
                    </td>
                    <td class="score-cell">${grade.score} / ${grade.max_points}</td>
                    <td class="percentage-cell">
                        <span class="percentage-badge ${gradeClass}">
                            ${percentage.toFixed(1)}%
                        </span>
                    </td>
                </tr>
            `;
        }).join('');

        return `
            <table class="grades-table">
                <thead>
                    <tr>
                        <th>Assignment</th>
                        <th>Score</th>
                        <th>Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    ${tableRows}
                </tbody>
            </table>
        `;
    }

    showLoading() {
        this.resultsSection.innerHTML = `
            <div class="loading">Loading your grades...</div>
        `;
        this.resultsSection.style.display = 'block';
    }

    showError(message) {
        GradeUtils.showError('resultsSection', message);
    }

    showNotFound(email) {
        this.resultsSection.innerHTML = `
            <div class="not-found">
                <h3>Student Not Found</h3>
                <p>No student found with email: <strong>${GradeUtils.escapeHtml(email)}</strong></p>
                <p>Please check your email address and try again.</p>
            </div>
        `;
        this.resultsSection.style.display = 'block';
    }
}

// Initialize based on page type
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('tableHeader')) {
        new GradesTable();
    } else if (document.getElementById('emailInput')) {
        new StudentPortal();
    }
});
