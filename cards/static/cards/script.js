document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-delete-dialog]").forEach(button => {
        const dialog = document.getElementById(button.dataset.deleteDialog);

        if (!(dialog instanceof HTMLDialogElement)) {
            return;
        }

        button.addEventListener("click", () => {
            dialog.showModal();
            dialog.querySelector("input[name='password']")?.focus();
        });

        dialog.querySelectorAll("[data-close-dialog]").forEach(closeButton => {
            closeButton.addEventListener("click", () => dialog.close());
        });

        dialog.addEventListener("click", event => {
            if (event.target === dialog) {
                dialog.close();
            }
        });
    });

    const cardNumber = document.getElementById("cardNumber");
    const cardHolder = document.getElementById("cardHolder");
    const expiry = document.getElementById("expiry");
    const previewNumber = document.getElementById("previewNumber");
    const previewHolder = document.getElementById("previewHolder");
    const previewExpiry = document.getElementById("previewExpiry");
    const cardType = document.getElementById("cardType");
    const previewType = document.getElementById("previewType");

    if (cardType && previewType) {
        cardType.addEventListener("change", () => {
            const labels = {
                Credit: "Credit",
                Debit: "Debit",
                Premium: "Premium"
            };
            previewType.textContent = labels[cardType.value] || "Card";
        });
    }

    if (cardNumber) {
        cardNumber.addEventListener("input", () => {
            let value = cardNumber.value.replace(/\D/g, "").slice(0, 16);
            value = value.match(/.{1,4}/g)?.join(" ") || "";
            cardNumber.value = value;
            previewNumber.textContent = value || "•••• •••• •••• ••••";
        });
    }

    if (cardHolder) {
        cardHolder.addEventListener("input", () => {
            const value = cardHolder.value.toUpperCase();
            previewHolder.textContent = value || "YOUR NAME";
        });
    }

    if (expiry) {
        expiry.addEventListener("input", () => {
            let value = expiry.value.replace(/\D/g, "").slice(0, 4);
            if (value.length > 2) value = value.slice(0, 2) + "/" + value.slice(2);
            expiry.value = value;
            previewExpiry.textContent = value || "MM/YY";
        });
    }

    const cvv = document.getElementById("cvv");

    if (cvv) {
        cvv.addEventListener("input", () => {
            cvv.value = cvv.value.replace(/\D/g, "").slice(0, 4);
        });
    }

    document.querySelectorAll(".type-option").forEach(option => {
        option.addEventListener("click", () => {
            document.querySelectorAll(".type-option").forEach(item => item.classList.remove("active"));
            option.classList.add("active");
            if (cardType) cardType.value = option.dataset.type;
        });
    });

    const creditCard = document.getElementById("creditCard");

    if (creditCard) {
        creditCard.addEventListener("mousemove", event => {
            const rect = creditCard.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            const rotateY = (x / rect.width - .5) * 10;
            const rotateX = (y / rect.height - .5) * -10;
            creditCard.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-5px)`;
        });

        creditCard.addEventListener("mouseleave", () => {
            creditCard.style.transform = "";
        });
    }

    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", () => {
            const button = form.querySelector(".submit-btn");
            if (button) {
                button.disabled = true;
                button.innerHTML = "Saving Card...";
            }
        });
    });
});