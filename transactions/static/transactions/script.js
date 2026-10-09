document.addEventListener("DOMContentLoaded", () => {
    const rows = document.querySelectorAll(".transaction-row");

    rows.forEach((row, index) => {
        row.style.opacity = "0";
        row.style.transform = "translateY(12px)";

        setTimeout(() => {
            row.style.transition = "opacity .4s ease, transform .4s ease";
            row.style.opacity = "1";
            row.style.transform = "translateY(0)";
        }, index * 70);
    });
});