// SmartMark Teacher Dashboard JS

// ── Help button ──────────────────────────────────────────────────────────────
document.querySelector(".help-btn")?.addEventListener("click", () => {
    alert(
        "SmartMark Teacher Help\n\n" +
        "• Select an hour from the dropdown, then click 'Enable Attendance'\n" +
        "• Attendance auto-closes after 5 minutes\n" +
        "• You can also click 'Close' to stop attendance early\n" +
        "• Students mark attendance via the Student Portal (/student/login)\n" +
        "• View Analytics & Reports from the sidebar\n\n" +
        "For support, contact admin."
    );
});

// ── 5-Minute Session Countdown Timers ────────────────────────────────────────
// ── Session Countdown Timers (Modified for Dynamic TTL) ───────────────────────

function initTimers() {
    const timers = document.querySelectorAll('.session-timer');
    if (!timers.length) return;

    timers.forEach(function (timerEl) {
        const sessionId = timerEl.dataset.sessionId;
        const createdAt = timerEl.dataset.createdAt;   // "YYYY-MM-DD HH:MM:SS"
        const ttl = parseInt(timerEl.closest('.session-row')?.dataset?.ttl || 5);
        const textEl = timerEl.querySelector('.timer-text');

        // SQLite stores CURRENT_TIMESTAMP as UTC — append 'Z' so JS Date parses it correctly
        const createdMs = new Date(createdAt.replace(' ', 'T') + 'Z').getTime();
        let expiresAt = createdMs + (ttl * 60 * 1000);
        console.log(`[Timer] Initialized session ${sessionId} - expires at: ${new Date(expiresAt)} (TTL: ${ttl}m)`);

        function tick() {
            const remaining = expiresAt - Date.now();

            if (remaining <= 0) {
                // Time's up – auto-close via AJAX
                textEl.textContent = '0:00';
                timerEl.style.background = '#dc2626';
                timerEl.style.color = '#fff';

                fetch('/teacher/api/close-session/' + sessionId, { method: 'POST' })
                    .then(function () {
                        var row = document.getElementById('session-row-' + sessionId);
                        if (row) {
                            row.style.transition = 'opacity 0.5s';
                            row.style.opacity = '0';
                            setTimeout(() => {
                                row.remove();
                                if (!document.querySelector('.session-row')) location.reload();
                            }, 600);
                        }
                    })
                    .catch(() => location.reload());
                return;
            }

            const totalSec = Math.ceil(remaining / 1000);
            const mins = Math.floor(totalSec / 60);
            const secs = totalSec % 60;
            textEl.textContent = mins + ':' + String(secs).padStart(2, '0');

            if (remaining < 60000) {
                timerEl.style.background = '#fffbeb';
                timerEl.style.borderColor = '#fde68a';
                timerEl.style.color = '#d97706';
            } else {
                timerEl.style.background = '#fef2f2';
                timerEl.style.borderColor = '#fecaca';
                timerEl.style.color = '#dc2626';
            }
            setTimeout(tick, 1000);
        }

        // ── Extension Logic ──────────────────────────────────────────────────
        var minsSelect = timerEl.parentElement.querySelector('.extend-mins-select');
        if (minsSelect) {
            minsSelect.onchange = function () {
                const addMins = parseInt(this.value);
                if (!addMins) return;
                minsSelect.disabled = true;
                fetch('/teacher/api/extend-session/' + sessionId, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ minutes: addMins })
                })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            expiresAt += (addMins * 60 * 1000);
                            timerEl.style.background = '#fef2f2';
                            timerEl.style.color = '#dc2626';
                        }
                    })
                    .finally(() => {
                        setTimeout(() => {
                            minsSelect.disabled = false;
                            minsSelect.value = "";
                        }, 500);
                    });
            };
        }

        tick();
    });
}

// ── Manual Mark Logic ─────────────────────────────────────────────────────────
function initManualMark() {
    const markButtons = document.querySelectorAll('.manual-mark-btn');

    markButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const sessionId = btn.dataset.sessionId;
            const searchContainer = document.getElementById('search-' + sessionId);
            searchContainer.classList.toggle('hidden');
            if (!searchContainer.classList.contains('hidden')) {
                searchContainer.querySelector('input').focus();
            }
        });
    });

    const searchInputs = document.querySelectorAll('.manual-student-search');
    searchInputs.forEach(input => {
        const container = input.closest('.manual-mark-search-container');
        const dropdown = container.querySelector('.search-results-dropdown');
        const sessionId = container.id.split('-')[1];

        function markManual(studentId, studentName = null) {
            const displayName = studentName || studentId;
            if (confirm(`Mark ${displayName} as present?`)) {
                fetch('/teacher/api/manual-mark-attendance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ student_id: studentId, session_id: sessionId })
                })
                    .then(res => res.json())
                    .then(resData => {
                        if (resData.success) {
                            alert("Attendance marked successfully!");
                            container.classList.add('hidden');
                            input.value = '';
                        } else {
                            alert("Error: " + resData.error);
                        }
                    });
            }
            dropdown.classList.add('hidden');
        }

        let timeout = null;
        input.addEventListener('input', () => {
            clearTimeout(timeout);
            const query = input.value.trim();
            if (query.length < 1) {
                dropdown.classList.add('hidden');
                return;
            }

            timeout = setTimeout(() => {
                console.log(`[ManualMark] Searching for: ${query}`);
                fetch(`/api/students/search?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.length === 0) {
                            dropdown.innerHTML = '<div style="padding:10px; font-size:12px; color:#999;">No results</div>';
                        } else {
                            dropdown.innerHTML = data.map(s => `
                                <div class="search-item" data-id="${s.id}" data-name="${s.name}"
                                     style="padding:8px 12px; cursor:pointer; border-bottom:1px solid #eee; font-size:13px;">
                                    <strong>${s.name}</strong> <small style="color:#666;">(${s.id})</small>
                                </div>
                            `).join('');

                            dropdown.querySelectorAll('.search-item').forEach(item => {
                                item.addEventListener('click', () => {
                                    markManual(item.dataset.id, item.dataset.name);
                                });
                            });
                        }
                        dropdown.classList.remove('hidden');
                    });
            }, 300);
        });

        // Handle Enter key to mark automatically if single result or perfect match
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const val = input.value.trim();
                if (!val) return;

                const items = dropdown.querySelectorAll('.search-item');
                // If single result or perfect ID match, use it
                if (items.length === 1) {
                    markManual(items[0].dataset.id, items[0].dataset.name);
                    return;
                }

                const perfectMatch = Array.from(items).find(item => item.dataset.id === val);
                if (perfectMatch) {
                    markManual(perfectMatch.dataset.id, perfectMatch.dataset.name);
                    return;
                }

                // Fallback: try marking the raw input directly as ID
                markManual(val);
            }
        });

        // Handle submit button click
        const submitBtn = container.querySelector('.manual-mark-submit-btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                const val = input.value.trim();
                if (val) markManual(val);
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) dropdown.classList.add('hidden');
        });
    });
}

// ── Dynamic OTP Fallback Logic ───────────────────────────────────────────────
function initOTPFallback() {
    const otpModal = document.getElementById('otp-modal');
    const otpContainer = document.getElementById('otp-code-container');
    const closeBtn = document.getElementById('close-otp-modal');
    const countdownEl = document.getElementById('otp-countdown');
    const otpButtons = document.querySelectorAll('.otp-display-btn');

    let refreshInterval = null;
    let countdownInterval = null;
    let activeSessionId = null;

    function updateOTP() {
        if (!activeSessionId) return;

        fetch(`/session/${activeSessionId}/otp`)
            .then(res => res.json())
            .then(data => {
                if (data.token) {
                    otpContainer.textContent = data.token;

                    // Sync countdown
                    let remaining = data.expires_in;
                    countdownEl.textContent = remaining;

                    clearInterval(countdownInterval);
                    countdownInterval = setInterval(() => {
                        remaining--;
                        if (remaining < 0) remaining = 0;
                        countdownEl.textContent = remaining;
                    }, 1000);
                }
            });
    }

    otpButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            activeSessionId = btn.dataset.sessionId;
            document.getElementById('otp-modal-title').textContent = `Attendance OTP: ${btn.dataset.subject}`;
            otpModal.style.display = 'flex';
            otpModal.classList.remove('hidden');

            updateOTP();
            refreshInterval = setInterval(updateOTP, 10000);
        });
    });

    function closeOTPModal() {
        otpModal.style.display = 'none';
        otpModal.classList.add('hidden');
        clearInterval(refreshInterval);
        clearInterval(countdownInterval);
        activeSessionId = null;
    }

    closeBtn?.addEventListener('click', closeOTPModal);
    window.addEventListener('click', (e) => {
        if (e.target === otpModal) closeOTPModal();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initTimers();
    initManualMark();
    initOTPFallback();
});

