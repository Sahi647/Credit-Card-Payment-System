document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toggle").forEach(button => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.target);
            input.type = input.type === "password" ? "text" : "password";
            button.textContent = input.type === "password" ? "👁" : "🙈";
        });
    });

    const password = document.getElementById("password");
    const strengthBar = document.getElementById("strengthBar");
    const strengthText = document.getElementById("strengthText");

    if (password) {
        password.addEventListener("input", () => {
            const value = password.value;
            let score = 0;

            if (value.length >= 8) score++;
            if (/[A-Z]/.test(value)) score++;
            if (/[0-9]/.test(value)) score++;
            if (/[^A-Za-z0-9]/.test(value)) score++;

            const widths = ["0%","25%","50%","75%","100%"];
            const labels = ["Enter a password","Weak password","Fair password","Strong password","Very strong password"];

            strengthBar.style.width = widths[score];
            strengthText.textContent = labels[score];
        });
    }

    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", () => {
            const button = form.querySelector(".submit-btn");

            if (button) {
                button.disabled = true;
                button.innerHTML = "Processing <span>...</span>";
            }
        });
    });
});