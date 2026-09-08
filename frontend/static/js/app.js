const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");

const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");

const sendButton = document.getElementById("send-button");
const voiceButton = document.getElementById("voice-button");


function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;

    return div.innerHTML;
}


function addMessage(role, text) {
    const wrapper = document.createElement("div");

    wrapper.className = `message ${role}`;

    const content = document.createElement("div");

    content.className = "message-content";
    content.innerHTML = escapeHtml(text);

    wrapper.appendChild(content);
    messages.appendChild(wrapper);

    messages.scrollTop = messages.scrollHeight;

    return wrapper;
}


function hideWelcome() {
    welcome.classList.add("hidden");
}


function setLoading(value) {
    sendButton.disabled = value;
    input.disabled = value;
}


function resizeInput() {
    input.style.height = "auto";

    input.style.height =
        `${Math.min(input.scrollHeight, 180)}px`;
}


async function sendMessage(message) {
    hideWelcome();

    addMessage(
        "user",
        message
    );

    const typingMessage = addMessage(
        "assistant",
        "Обрабатываю запрос..."
    );

    typingMessage
        .querySelector(".message-content")
        .classList.add("typing");

    setLoading(true);

    try {

        const response = await fetch(
            "/api/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message
                })
            }
        );


        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data = await response.json();

        typingMessage.remove();

        addMessage(
            "assistant",
            data.answer
        );

    } catch (error) {

        console.error(error);

        typingMessage.remove();

        addMessage(
            "assistant",
            "Не удалось выполнить запрос. Проверьте соединение с SD.OS."
        );

    } finally {

        setLoading(false);

        input.focus();

    }
}


form.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();

        const message = input.value.trim();

        if (!message) {
            return;
        }

        input.value = "";
        resizeInput();

        await sendMessage(message);
    }
);


input.addEventListener(
    "input",
    resizeInput
);


input.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Enter"
            && !event.shiftKey
        ) {

            event.preventDefault();

            form.requestSubmit();
        }
    }
);


voiceButton.addEventListener(
    "click",
    () => {

        addMessage(
            "assistant",
            "Голосовой ввод будет подключён следующим этапом."
        );

        hideWelcome();

    }
);


input.focus();