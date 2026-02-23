document.querySelectorAll(".enable-btn").forEach(button => {
document.querySelector(".help-btn")?.addEventListener("click", () => {
    alert(
        "SmartMark Help\n\n" +
        "• Enable attendance from subject cards\n" +
        "• Attendance auto-disables after 5 minutes\n" +
        "• View reports from Attendance Report\n\n" +
        "For support, contact admin."
    );
});

    button.addEventListener("click", () => {

        const card = button.closest(".subject-card");
        const timerBox = card.querySelector(".attendance-timer");
        const timerText = card.querySelector(".timer-text");
        const statusText = card.querySelector(".timer-status");
        const progressCircle = card.querySelector(".timer-progress");

        const duration = 300;
        let remaining = duration;

        const radius = 55;
        const circumference = 2 * Math.PI * radius;

        progressCircle.style.strokeDasharray = circumference;
        progressCircle.style.strokeDashoffset = 0;

        button.classList.add("hidden");
        timerBox.classList.remove("hidden");

        const interval = setInterval(() => {
            remaining--;

            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;

            timerText.textContent =
                `${minutes}:${seconds.toString().padStart(2, "0")}`;

            progressCircle.style.strokeDashoffset =
                circumference - (remaining / duration) * circumference;

            if (remaining <= 0) {
                clearInterval(interval);
                statusText.textContent = "Attendance Disabled";
                statusText.style.color = "#ef4444";

                setTimeout(() => {
                    timerBox.classList.add("hidden");
                    button.classList.remove("hidden");
                    timerText.textContent = "05:00";
                    statusText.textContent = "Attendance Active";
                    statusText.style.color = "#22c55e";
                    progressCircle.style.strokeDashoffset = 0;
                }, 1500);
            }
        }, 1000);
    });

});
