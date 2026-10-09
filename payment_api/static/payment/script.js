const accessTokenInput = document.getElementById("accessToken");
const cardSelect = document.getElementById("cardId");
const cardLastFourInput = document.getElementById("cardLastFour");
const amountInput = document.getElementById("amount");
const messageBox = document.getElementById("message");
const payButton = document.getElementById("payButton");
const resultPanel = document.getElementById("resultPanel");
const paymentApiBase = `${window.location.pathname.replace(/\/$/, "")}/api/payments`;
let currentPaymentId;

function authorizationHeaders(json = false) {
    const headers = { Authorization: `Bearer ${accessTokenInput.value.trim()}` };
    if (json) {
        headers["Content-Type"] = "application/json";
    }
    return headers;
}

function showWarning(message) {
    messageBox.style.display = "block";
    messageBox.textContent = message;
}

function hideMessage() {
    messageBox.style.display = "none";
    messageBox.textContent = "";
}

async function readResponse(response) {
    const data = await response.json();
    if (!response.ok) {
        const detail = data.detail;
        if (Array.isArray(detail)) {
            const messages = detail.map(item => item.msg).filter(Boolean);
            throw new Error(messages.join(" ") || "Please check the information and try again.");
        }
        throw new Error(typeof detail === "string" ? detail : "Please check the information and try again.");
    }
    return data;
}

function updateCardPreview() {
    const option = cardSelect.options[cardSelect.selectedIndex];
    if (!option || !option.value) {
        document.getElementById("previewCard").textContent = "•••• •••• •••• ••••";
        document.getElementById("previewHolder").textContent = "YOUR NAME";
        cardLastFourInput.value = "";
        return;
    }
    document.getElementById("previewCard").textContent =
        `•••• •••• •••• ${option.dataset.lastFour}`;
    document.getElementById("previewHolder").textContent =
        option.dataset.holder.toUpperCase();
    cardLastFourInput.value = "";
}

async function loadCards() {
    hideMessage();
    if (!accessTokenInput.value.trim()) {
        showWarning("Enter your JWT access token to load your card profiles.");
        accessTokenInput.focus();
        return;
    }
    try {
        const response = await fetch(`${paymentApiBase}/cards/`, {
            headers: authorizationHeaders()
        });
        const cards = await readResponse(response);
        cardSelect.innerHTML = '<option value="">Select a card profile</option>';
        if (!Array.isArray(cards) || cards.length === 0) {
            updateCardPreview();
            showWarning("Add a card profile to your account before starting a payment.");
            return;
        }
        cards.forEach(card => {
            const option = document.createElement("option");
            option.value = card.id;
            option.dataset.lastFour = card.last_four;
            option.dataset.holder = card.card_holder;
            option.textContent = `${card.card_type} - ${card.masked_number}`;
            cardSelect.appendChild(option);
        });
    } catch (error) {
        showWarning(error.message || "Unable to load saved cards. Please try again.");
    }
}

async function makePayment() {
    hideMessage();
    resultPanel.style.display = "none";
    const cardId = Number(cardSelect.value);
    const cardLastFour = cardLastFourInput.value.trim();
    const amount = amountInput.value;
    const numericAmount = Number(amount);

    if (!accessTokenInput.value.trim()) {
        showWarning("Enter your JWT access token before continuing.");
        accessTokenInput.focus();
        return;
    }
    if (!Number.isInteger(cardId) || cardId < 1) {
        showWarning("Choose a card profile before continuing.");
        cardSelect.focus();
        return;
    }
    if (!/^\d{4}$/.test(cardLastFour)) {
        showWarning("Enter the last four digits of the selected card.");
        cardLastFourInput.focus();
        return;
    }
    if (!Number.isFinite(numericAmount) || numericAmount <= 0 || numericAmount > 1000000) {
        showWarning("Enter an amount greater than ₹0 and no more than ₹1,000,000.");
        amountInput.focus();
        return;
    }

    payButton.disabled = true;
    payButton.textContent = "Verifying Card Details...";
    try {
        const createResponse = await fetch(`${paymentApiBase}/`, {
            method: "POST",
            headers: authorizationHeaders(true),
            body: JSON.stringify({
                card_id: cardId,
                card_last_four: cardLastFour,
                amount
            })
        });
        const payment = await readResponse(createResponse);
        currentPaymentId = payment.payment_id;
        showResult(payment);
    } catch (error) {
        showWarning(error.message || "The payment could not be recorded. Please check the details.");
    } finally {
        payButton.disabled = false;
        payButton.textContent = "Make Simulated Payment";
    }
}

async function refreshPaymentStatus() {
    if (!currentPaymentId || !accessTokenInput.value.trim()) {
        showWarning("Enter your JWT access token to check this payment's status.");
        return;
    }
    try {
        const response = await fetch(
            `${paymentApiBase}/${encodeURIComponent(currentPaymentId)}`,
            { headers: authorizationHeaders() }
        );
        const payment = await readResponse(response);
        showResult({
            payment_id: payment.payment_id,
            status: payment.status,
            message: "Simulation only. No real money was charged."
        });
    } catch (error) {
        showWarning(error.message || "Unable to retrieve this payment's status.");
    }
}

function resetPaymentForm() {
    currentPaymentId = undefined;
    document.getElementById("refreshPaymentButton").hidden = true;
    document.getElementById("newPaymentButton").hidden = true;
    payButton.hidden = false;
    payButton.disabled = false;
    document.getElementById("previewStatus").textContent = "READY";
    resultPanel.style.display = "none";
    hideMessage();
}

function showResult(result) {
    const panel = resultPanel;
    const icon = document.getElementById("resultIcon");
    const succeeded = result.status === "SUCCESS";
    panel.style.display = "block";
    panel.classList.toggle("warning-result", !succeeded);
    document.getElementById("paymentId").textContent = result.payment_id;
    document.getElementById("paymentStatus").textContent = result.status;
    document.getElementById("resultMessage").textContent = result.message;
    document.getElementById("previewStatus").textContent = result.status;
    document.getElementById("refreshPaymentButton").hidden = false;
    document.getElementById("newPaymentButton").hidden = false;

    if (succeeded) {
        icon.textContent = "✓";
        icon.style.color = "#4ade80";
        document.getElementById("resultTitle").textContent = "Simulation Successful";
    } else {
        icon.textContent = "!";
        icon.style.color = "#fde68a";
        document.getElementById("resultTitle").textContent =
            result.status === "FAILED" ? "Payment Not Completed" : "Payment Needs Attention";
    }
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
}

document.getElementById("previewStatus").textContent = "READY";
