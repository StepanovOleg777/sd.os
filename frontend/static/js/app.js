const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");

const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");

const sendButton = document.getElementById("send-button");
const voiceButton = document.getElementById("voice-button");

const composer = document.querySelector(".composer");

const newChatButton =
    document.getElementById("ai-new-chat");

const conversationList =
    document.getElementById("ai-conversation-list");

let currentConversationId = null;


// =========================================================
// UI
// =========================================================

const DEFAULT_PLACEHOLDER =
    "Чем я могу помочь?";

input.placeholder =
    DEFAULT_PLACEHOLDER;


// =========================================================
// Voice waveform
// =========================================================

const waveformContainer =
    document.createElement("div");

waveformContainer.className =
    "voice-waveform-live";

waveformContainer.hidden =
    true;


const waveformCanvas =
    document.createElement("canvas");

waveformCanvas.className =
    "voice-waveform-canvas";


waveformContainer.appendChild(
    waveformCanvas
);


composer.appendChild(
    waveformContainer
);


const waveformContext =
    waveformCanvas.getContext("2d");


// =========================================================
// Recording state
// =========================================================

let mediaRecorder = null;
let mediaStream = null;

let audioChunks = [];

let isRecording = false;


// =========================================================
// Audio analyser
// =========================================================

let audioContext = null;
let analyser = null;
let analyserSource = null;

let animationFrame = null;

let recordingStartedAt = 0;
let lastSoundAt = 0;

let heardSpeech = false;


// =========================================================
// Voice settings
// =========================================================

const SILENCE_DURATION = 1800;

const SILENCE_THRESHOLD = 0.018;

const MAX_RECORDING_DURATION =
    30_000;


// =========================================================
// Waveform settings
// =========================================================

const WAVEFORM_POINTS = 90;

const WAVEFORM_GAIN = 2.35;

const TEMPORAL_SMOOTHING = 0.38;

const SPATIAL_SMOOTHING = 2;


let previousWaveform =
    new Array(
        WAVEFORM_POINTS
    ).fill(0);


let visualLevel = 0;


// =========================================================
// Chat UI
// =========================================================

function addMessage(role, text) {
    const wrapper =
        document.createElement("div");

    wrapper.className =
        `message ${role}`;


    const content =
        document.createElement("div");

    content.className =
        "message-content";

    content.textContent =
        text;


    wrapper.appendChild(
        content
    );


    messages.appendChild(
        wrapper
    );


    scrollMessagesToBottom();


    return wrapper;
}


function createActionLink(
    label,
    href
) {
    const button =
        document.createElement("a");

    button.className =
        "message-action-button";

    button.href =
        href;

    button.textContent =
        label;

    return button;
}


function createActionButton(
    label
) {
    const button =
        document.createElement("button");

    button.type =
        "button";

    button.className =
        "message-action-button";

    button.textContent =
        label;

    return button;
}


function addDirectAction(
    messageElement,
    action
) {
    if (
        !action
        ||
        !action.href
    ) {
        return;
    }


    const content =
        messageElement.querySelector(
            ".message-content"
        );


    if (!content) {
        return;
    }


    const actions =
        document.createElement("div");

    actions.className =
        "message-actions";


    const defaultLabel =
        action.type === "email"
            ? "Написать письмо"
            : "Позвонить";


    const button =
        createActionLink(
            action.label
            || defaultLabel,
            action.href
        );


    actions.appendChild(
        button
    );


    content.appendChild(
        actions
    );


    scrollMessagesToBottom();
}


function addChoiceButtons(
    messageElement,
    action
) {
    if (
        !action
        ||
        !Array.isArray(
            action.choices
        )
        ||
        action.choices.length === 0
    ) {
        return;
    }


    const content =
        messageElement.querySelector(
            ".message-content"
        );


    if (!content) {
        return;
    }


    const actions =
        document.createElement("div");

    actions.className =
        "message-actions";


    action.choices.forEach(
        choice => {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "message-action-row";


            if (
                action.type
                === "choose_phone"
            ) {
                if (!choice.href) {
                    return;
                }


                const button =
                    createActionLink(
                        choice.label
                        || choice.value,
                        choice.href
                    );


                row.appendChild(
                    button
                );


                actions.appendChild(
                    row
                );


                return;
            }


            if (
                action.type
                === "choose_person"
            ) {
                if (!choice.value) {
                    return;
                }


                const button =
                    createActionButton(
                        choice.label
                        || choice.value
                    );


                button.addEventListener(
                    "click",
                    async () => {

                        if (
                            action.intent
                            === "email"
                        ) {
                            await sendMessage(
                                `Напиши ${choice.value}`
                            );

                            return;
                        }


                        await sendMessage(
                            `Позвони ${choice.value}`
                        );
                    }
                );


                row.appendChild(
                    button
                );


                actions.appendChild(
                    row
                );
            }

        }
    );


    if (
        actions.children.length === 0
    ) {
        return;
    }


    content.appendChild(
        actions
    );


    scrollMessagesToBottom();
}


function renderAssistantResponse(
    data
) {
    const assistantMessage =
        addMessage(
            "assistant",
            data.answer
            || ""
        );


    if (!data.action) {
        return;
    }


    if (
        data.action.type
        === "call"
        ||
        data.action.type
        === "email"
    ) {
        addDirectAction(
            assistantMessage,
            data.action
        );

        return;
    }


    if (
        data.action.type
        === "choose_person"
        ||
        data.action.type
        === "choose_phone"
    ) {
        addChoiceButtons(
            assistantMessage,
            data.action
        );
    }
}


function scrollMessagesToBottom() {
    requestAnimationFrame(() => {
        messages.scrollTop =
            messages.scrollHeight;
    });
}


function hideWelcome() {
    welcome.classList.add(
        "hidden"
    );
}


function showWelcome() {
    welcome.classList.remove(
        "hidden"
    );
}


// =========================================================
// AI conversations
// =========================================================

function clearMessages() {
    messages.innerHTML = "";
}


function setActiveConversationItem(
    conversationId
) {
    if (!conversationList) {
        return;
    }

    conversationList
        .querySelectorAll(
            ".ai-conversation-row"
        )
        .forEach(item => {

            item.classList.toggle(
                "active",
                item.dataset.conversationId
                === conversationId
            );
        });
}


function renderConversationList(
    conversations
) {
    if (!conversationList) {
        return;
    }

    conversationList.innerHTML = "";

    if (
        !Array.isArray(conversations)
        ||
        conversations.length === 0
    ) {
        const empty =
            document.createElement("div");

        empty.className =
            "ai-conversation-list-empty";

        empty.textContent =
            "Пока нет чатов";

        conversationList.appendChild(
            empty
        );

        return;
    }

    conversations.forEach(
        conversation => {

            const row =
                document.createElement("div");

            row.className =
                "ai-conversation-row";

            row.dataset.conversationId =
                conversation.conversation_id;


            if (
                conversation.conversation_id
                === currentConversationId
            ) {
                row.classList.add(
                    "active"
                );
            }


            const openButton =
                document.createElement("button");

            openButton.type =
                "button";

            openButton.className =
                "ai-conversation-item";

            openButton.textContent =
                conversation.title
                || "Новый чат";


            openButton.addEventListener(
                "click",
                async () => {
                    await openConversation(
                        conversation
                            .conversation_id
                    );
                }
            );


            const renameButton =
                document.createElement("button");

            renameButton.type =
                "button";

            renameButton.className =
                "ai-conversation-rename";

            renameButton.setAttribute(
                "aria-label",
                "Переименовать чат"
            );

            renameButton.setAttribute(
                "title",
                "Переименовать чат"
            );

            renameButton.textContent =
                "✎";


            renameButton.addEventListener(
                "click",
                async event => {

                    event.stopPropagation();

                    await renameConversation(
                        conversation,
                        row,
                        openButton
                    );
                }
            );


            const deleteButton =
                document.createElement("button");

            deleteButton.type =
                "button";

            deleteButton.className =
                "ai-conversation-delete";

            deleteButton.setAttribute(
                "aria-label",
                "Удалить чат"
            );

            deleteButton.setAttribute(
                "title",
                "Удалить чат"
            );

            deleteButton.textContent =
                "×";


            deleteButton.addEventListener(
                "click",
                async event => {

                    event.stopPropagation();

                    await deleteConversation(
                        conversation
                            .conversation_id
                    );
                }
            );


            row.appendChild(
                openButton
            );

            row.appendChild(
                renameButton
            );

            row.appendChild(
                deleteButton
            );

            conversationList.appendChild(
                row
            );
        }
    );
}


async function loadConversations() {
    if (!conversationList) {
        return;
    }

    try {
        const response =
            await fetch(
                "/api/chat/conversations"
            );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        renderConversationList(
            data
        );

    } catch (error) {
        console.error(
            "Не удалось загрузить AI-чаты:",
            error
        );

        conversationList.innerHTML = "";

        const errorElement =
            document.createElement("div");

        errorElement.className =
            "ai-conversation-list-empty";

        errorElement.textContent =
            "Не удалось загрузить чаты";

        conversationList.appendChild(
            errorElement
        );
    }
}


async function openConversation(
    conversationId
) {
    setLoading(true);

    try {
        const response =
            await fetch(
                `/api/chat/conversations/${conversationId}`
            );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        currentConversationId =
            data.conversation_id;

        clearMessages();

        const history =
            Array.isArray(data.messages)
                ? data.messages
                : [];

        if (history.length === 0) {
            showWelcome();
        } else {
            hideWelcome();

            history.forEach(
                message => {
                    if (
                        message.role !== "user"
                        &&
                        message.role !== "assistant"
                    ) {
                        return;
                    }

                    addMessage(
                        message.role,
                        message.text || ""
                    );
                }
            );
        }

        setActiveConversationItem(
            currentConversationId
        );

    } catch (error) {
        console.error(
            "Не удалось открыть AI-чат:",
            error
        );

    } finally {
        setLoading(false);
        input.focus();
    }
}


async function renameConversation(
    conversation,
    row,
    openButton
) {
    if (
        row.classList.contains(
            "editing"
        )
    ) {
        return;
    }

    row.classList.add(
        "editing"
    );


    const originalTitle =
        conversation.title
        || "Новый чат";


    const inputElement =
        document.createElement("input");

    inputElement.type =
        "text";

    inputElement.className =
        "ai-conversation-edit-input";

    inputElement.value =
        originalTitle;

    inputElement.maxLength =
        255;


    openButton.replaceWith(
        inputElement
    );


    const finishEditing =
        async save => {

            if (
                !row.classList.contains(
                    "editing"
                )
            ) {
                return;
            }

            const title =
                inputElement.value.trim();


            if (!save) {
                row.classList.remove(
                    "editing"
                );

                inputElement.replaceWith(
                    openButton
                );

                return;
            }


            if (!title) {
                inputElement.focus();

                return;
            }


            if (
                title === originalTitle
            ) {
                row.classList.remove(
                    "editing"
                );

                inputElement.replaceWith(
                    openButton
                );

                return;
            }


            inputElement.disabled =
                true;


            try {
                const response =
                    await fetch(
                        `/api/chat/conversations/${conversation.conversation_id}`,
                        {
                            method: "PATCH",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    title
                                })
                        }
                    );


                if (!response.ok) {
                    throw new Error(
                        `HTTP ${response.status}`
                    );
                }


                conversation.title =
                    title;

                openButton.textContent =
                    title;


                row.classList.remove(
                    "editing"
                );

                inputElement.replaceWith(
                    openButton
                );


            } catch (error) {
                console.error(
                    "Не удалось переименовать AI-чат:",
                    error
                );

                inputElement.disabled =
                    false;

                inputElement.focus();
            }
        };


    inputElement.addEventListener(
        "keydown",
        async event => {

            if (
                event.key === "Enter"
            ) {
                event.preventDefault();

                await finishEditing(
                    true
                );

                return;
            }


            if (
                event.key === "Escape"
            ) {
                event.preventDefault();

                await finishEditing(
                    false
                );
            }
        }
    );


    inputElement.addEventListener(
        "blur",
        async () => {
            await finishEditing(
                true
            );
        }
    );


    inputElement.focus();

    inputElement.select();
}


async function deleteConversation(
    conversationId
) {
    const confirmed =
        window.confirm(
            "Удалить этот чат?"
        );

    if (!confirmed) {
        return;
    }


    try {
        const response =
            await fetch(
                `/api/chat/conversations/${conversationId}`,
                {
                    method: "DELETE"
                }
            );


        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }


        if (
            currentConversationId
            === conversationId
        ) {
            startNewConversation();
        }


        await loadConversations();

    } catch (error) {
        console.error(
            "Не удалось удалить AI-чат:",
            error
        );

        window.alert(
            "Не удалось удалить чат."
        );
    }
}


function startNewConversation() {
    currentConversationId = null;

    clearMessages();
    showWelcome();

    setActiveConversationItem(
        null
    );

    input.value = "";
    resizeInput();
    input.focus();
}


if (newChatButton) {
    newChatButton.addEventListener(
        "click",
        startNewConversation
    );
}


loadConversations();


function setLoading(value) {
    sendButton.disabled =
        value;

    input.disabled =
        value;
}


function resizeInput() {
    input.style.height =
        "auto";


    input.style.height =
        `${Math.min(
            input.scrollHeight,
            180
        )}px`;
}


// =========================================================
// Chat request
// =========================================================

async function sendMessage(message) {
    const wasNewConversation =
        currentConversationId === null;

    hideWelcome();


    addMessage(
        "user",
        message
    );


    const typingMessage =
        addMessage(
            "assistant",
            "Обрабатываю запрос..."
        );


    typingMessage
        .querySelector(
            ".message-content"
        )
        .classList.add(
            "typing"
        );


    setLoading(true);


    try {
        const response =
            await fetch(
                "/api/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            message,
                            conversation_id:
                                currentConversationId
                        })
                }
            );


        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();

        if (data.conversation_id) {
            currentConversationId =
                data.conversation_id;
        }

        typingMessage.remove();


        renderAssistantResponse(
            data
        );


        if (wasNewConversation) {
            await loadConversations();
        } else {
            setActiveConversationItem(
                currentConversationId
            );
        }

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


// =========================================================
// Audio format
// =========================================================

function getSupportedMimeType() {
    const types = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/ogg",
        "audio/mp4"
    ];


    return types.find(
        type =>
            MediaRecorder
                .isTypeSupported(type)
    ) || "";
}


function getFileExtension(
    mimeType
) {
    if (
        mimeType.includes("ogg")
    ) {
        return "ogg";
    }


    if (
        mimeType.includes("mp4")
    ) {
        return "mp4";
    }


    return "webm";
}
// =========================================================
// Waveform visibility
// =========================================================

function showWaveform() {
    input.classList.add(
        "voice-input-hidden"
    );


    waveformContainer.hidden =
        false;


    waveformContainer.classList.add(
        "active"
    );


    previousWaveform =
        new Array(
            WAVEFORM_POINTS
        ).fill(0);


    visualLevel = 0;


    resizeWaveformCanvas();


    drawFlatLine();
}


function hideWaveform() {
    waveformContainer.classList.remove(
        "active"
    );


    waveformContainer.hidden =
        true;


    input.classList.remove(
        "voice-input-hidden"
    );


    previousWaveform =
        new Array(
            WAVEFORM_POINTS
        ).fill(0);


    visualLevel = 0;


    clearWaveform();
}


// =========================================================
// Canvas
// =========================================================

function resizeWaveformCanvas() {
    const rect =
        waveformContainer
            .getBoundingClientRect();


    if (
        rect.width <= 0
        ||
        rect.height <= 0
    ) {
        return;
    }


    const dpr =
        Math.min(
            window.devicePixelRatio || 1,
            2
        );


    waveformCanvas.width =
        Math.round(
            rect.width * dpr
        );


    waveformCanvas.height =
        Math.round(
            rect.height * dpr
        );


    waveformCanvas.style.width =
        `${rect.width}px`;

    waveformCanvas.style.height =
        `${rect.height}px`;


    waveformContext.setTransform(
        dpr,
        0,
        0,
        dpr,
        0,
        0
    );
}


function clearWaveform() {
    const rect =
        waveformCanvas
            .getBoundingClientRect();


    waveformContext.clearRect(
        0,
        0,
        rect.width,
        rect.height
    );
}


// =========================================================
// Flat line
// =========================================================

function drawFlatLine() {
    const rect =
        waveformCanvas
            .getBoundingClientRect();


    const width =
        rect.width;

    const height =
        rect.height;


    if (
        width <= 0
        ||
        height <= 0
    ) {
        return;
    }


    waveformContext.clearRect(
        0,
        0,
        width,
        height
    );


    waveformContext.beginPath();


    waveformContext.moveTo(
        0,
        height / 2
    );


    waveformContext.lineTo(
        width,
        height / 2
    );


    waveformContext.strokeStyle =
        "rgba(255, 255, 255, 0.82)";


    waveformContext.lineWidth =
        1.35;


    waveformContext.lineCap =
        "round";


    waveformContext.stroke();
}


// =========================================================
// Waveform helpers
// =========================================================

function calculateRms(
    dataArray
) {
    let sumSquares = 0;


    for (
        let i = 0;
        i < dataArray.length;
        i++
    ) {
        const value =
            dataArray[i];


        sumSquares +=
            value * value;
    }


    return Math.sqrt(
        sumSquares
        /
        dataArray.length
    );
}


function calculatePeak(
    dataArray
) {
    let peak = 0;


    for (
        let i = 0;
        i < dataArray.length;
        i++
    ) {
        const value =
            Math.abs(
                dataArray[i]
            );


        if (value > peak) {
            peak = value;
        }
    }


    return peak;
}


// =========================================================
// Spatial smoothing
// =========================================================

function smoothWaveformPoints(
    points,
    radius
) {
    const result =
        new Array(
            points.length
        );


    for (
        let i = 0;
        i < points.length;
        i++
    ) {
        let sum = 0;
        let count = 0;


        const start =
            Math.max(
                0,
                i - radius
            );


        const end =
            Math.min(
                points.length - 1,
                i + radius
            );


        for (
            let j = start;
            j <= end;
            j++
        ) {
            sum +=
                points[j];

            count++;
        }


        result[i] =
            sum / count;
    }


    return result;
}


// =========================================================
// Draw waveform
// =========================================================

function drawWaveform(
    dataArray
) {
    const rect =
        waveformCanvas
            .getBoundingClientRect();


    const width =
        rect.width;

    const height =
        rect.height;


    if (
        width <= 0
        ||
        height <= 0
    ) {
        return;
    }


    const rms =
        calculateRms(
            dataArray
        );


    const peak =
        calculatePeak(
            dataArray
        );


    const visualNoiseFloor =
        0.008;


    let targetLevel = 0;


    if (
        rms > visualNoiseFloor
    ) {
        targetLevel =
            Math.min(
                (
                    rms
                    - visualNoiseFloor
                )
                * 28,
                1
            );
    }


    if (
        targetLevel >
        visualLevel
    ) {
        visualLevel =
            visualLevel * 0.28
            +
            targetLevel * 0.72;

    } else {
        visualLevel =
            visualLevel * 0.68
            +
            targetLevel * 0.32;
    }


    if (
        visualLevel < 0.025
    ) {
        visualLevel = 0;
    }


    const rawPoints =
        new Array(
            WAVEFORM_POINTS
        );


    const sampleStep =
        (
            dataArray.length - 1
        )
        /
        (
            WAVEFORM_POINTS - 1
        );


    const normalization =
        peak > 0.001
            ? 1 / peak
            : 0;


    for (
        let i = 0;
        i < WAVEFORM_POINTS;
        i++
    ) {
        const index =
            Math.floor(
                i * sampleStep
            );


        const rawSample =
            dataArray[index];


        let value =
            rawSample
            * normalization;


        value =
            Math.max(
                -1,
                Math.min(
                    1,
                    value
                )
            );


        rawPoints[i] =
            value;
    }


    const spatialPoints =
        smoothWaveformPoints(
            rawPoints,
            SPATIAL_SMOOTHING
        );


    const currentWaveform =
        new Array(
            WAVEFORM_POINTS
        );


    for (
        let i = 0;
        i < WAVEFORM_POINTS;
        i++
    ) {
        const target =
            spatialPoints[i]
            *
            visualLevel;


        currentWaveform[i] =
            previousWaveform[i]
            * TEMPORAL_SMOOTHING
            +
            target
            * (
                1
                - TEMPORAL_SMOOTHING
            );
    }


    previousWaveform =
        currentWaveform;


    waveformContext.clearRect(
        0,
        0,
        width,
        height
    );


    waveformContext.strokeStyle =
        "rgba(255, 255, 255, 0.84)";


    waveformContext.lineWidth =
        1.35;


    waveformContext.lineCap =
        "round";


    waveformContext.lineJoin =
        "round";


    const centerY =
        height / 2;


    const maxAmplitude =
        height
        * 0.6
        * WAVEFORM_GAIN;


    const safeAmplitude =
        Math.min(
            maxAmplitude,
            height * 0.43
        );


    waveformContext.beginPath();


    const points = [];


    for (
        let i = 0;
        i < currentWaveform.length;
        i++
    ) {
        const progress =
            i
            /
            (
                currentWaveform.length - 1
            );


        const edge =
            Math.sin(
                Math.PI * progress
            );


        const edgeEnvelope =
            0.30
            +
            edge * 0.70;


        const x =
            progress * width;


        const y =
            centerY
            +
            currentWaveform[i]
            *
            safeAmplitude
            *
            edgeEnvelope;


        points.push({
            x,
            y
        });
    }


    if (
        points.length > 0
    ) {
        waveformContext.moveTo(
            points[0].x,
            points[0].y
        );


        for (
            let i = 1;
            i < points.length - 1;
            i++
        ) {
            const current =
                points[i];


            const next =
                points[i + 1];


            const midX =
                (
                    current.x
                    +
                    next.x
                ) / 2;


            const midY =
                (
                    current.y
                    +
                    next.y
                ) / 2;


            waveformContext
                .quadraticCurveTo(
                    current.x,
                    current.y,
                    midX,
                    midY
                );
        }


        const last =
            points[
                points.length - 1
            ];


        waveformContext.lineTo(
            last.x,
            last.y
        );
    }


    waveformContext.stroke();
}


// =========================================================
// Start recording
// =========================================================

async function startRecording() {
    if (
        !navigator.mediaDevices
        ||
        !navigator.mediaDevices
            .getUserMedia
        ||
        typeof MediaRecorder
            === "undefined"
    ) {
        addMessage(
            "assistant",
            "Этот браузер не поддерживает запись с микрофона."
        );


        hideWelcome();


        return;
    }


    try {
        mediaStream =
            await navigator
                .mediaDevices
                .getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });


        const mimeType =
            getSupportedMimeType();


        const options =
            mimeType
                ? {
                    mimeType
                }
                : undefined;


        mediaRecorder =
            new MediaRecorder(
                mediaStream,
                options
            );


        audioChunks = [];


        mediaRecorder.addEventListener(
            "dataavailable",
            event => {

                if (
                    event.data.size > 0
                ) {
                    audioChunks.push(
                        event.data
                    );
                }

            }
        );


        mediaRecorder.addEventListener(
            "stop",
            async () => {

                const actualMimeType =
                    mediaRecorder.mimeType
                    ||
                    mimeType
                    ||
                    "audio/webm";


                const audioBlob =
                    new Blob(
                        audioChunks,
                        {
                            type:
                                actualMimeType
                        }
                    );


                await stopAudioAnalysis();


                stopMediaStream();


                await transcribeAudio(
                    audioBlob,
                    actualMimeType
                );

            }
        );


        mediaRecorder.start();


        isRecording = true;


        voiceButton.classList.add(
            "recording"
        );


        voiceButton.setAttribute(
            "aria-label",
            "Остановить запись"
        );


        voiceButton.setAttribute(
            "title",
            "Остановить запись"
        );


        showWaveform();


        startAudioAnalysis();

    } catch (error) {
        console.error(error);


        isRecording = false;


        voiceButton.classList.remove(
            "recording"
        );


        hideWaveform();


        await stopAudioAnalysis();


        stopMediaStream();


        addMessage(
            "assistant",
            "Не удалось получить доступ к микрофону."
        );


        hideWelcome();
    }
}


// =========================================================
// Stop recording
// =========================================================

function stopRecording() {
    if (
        !mediaRecorder
        ||
        mediaRecorder.state
            === "inactive"
    ) {
        return;
    }


    isRecording = false;


    mediaRecorder.stop();


    voiceButton.classList.remove(
        "recording"
    );


    voiceButton.setAttribute(
        "aria-label",
        "Голосовой ввод"
    );


    voiceButton.setAttribute(
        "title",
        "Голосовой ввод"
    );


    hideWaveform();
}


// =========================================================
// Audio analysis
// =========================================================

function startAudioAnalysis() {
    const AudioContextClass =
        window.AudioContext
        ||
        window.webkitAudioContext;


    if (!AudioContextClass) {
        return;
    }


    audioContext =
        new AudioContextClass();


    analyser =
        audioContext
            .createAnalyser();


    analyser.fftSize =
        2048;


    analyser.smoothingTimeConstant =
        0.18;


    analyserSource =
        audioContext
            .createMediaStreamSource(
                mediaStream
            );


    analyserSource.connect(
        analyser
    );


    const dataArray =
        new Float32Array(
            analyser.fftSize
        );


    recordingStartedAt =
        performance.now();


    lastSoundAt =
        recordingStartedAt;


    heardSpeech = false;


    function update() {
        if (
            !isRecording
            ||
            !analyser
        ) {
            return;
        }


        analyser.getFloatTimeDomainData(
            dataArray
        );


        drawWaveform(
            dataArray
        );


        const rms =
            calculateRms(
                dataArray
            );


        const now =
            performance.now();


        if (
            rms >
            SILENCE_THRESHOLD
        ) {
            heardSpeech =
                true;


            lastSoundAt =
                now;
        }


        if (
            heardSpeech
            &&
            now - lastSoundAt
            >= SILENCE_DURATION
        ) {
            stopRecording();

            return;
        }


        if (
            now - recordingStartedAt
            >= MAX_RECORDING_DURATION
        ) {
            stopRecording();

            return;
        }


        animationFrame =
            requestAnimationFrame(
                update
            );
    }


    animationFrame =
        requestAnimationFrame(
            update
        );
}
// =========================================================
// Stop audio analysis
// =========================================================

async function stopAudioAnalysis() {
    if (animationFrame) {
        cancelAnimationFrame(
            animationFrame
        );


        animationFrame = null;
    }


    if (analyserSource) {
        try {
            analyserSource.disconnect();

        } catch (_) {
            // Уже отключён.
        }


        analyserSource = null;
    }


    analyser = null;


    if (audioContext) {
        try {
            await audioContext.close();

        } catch (_) {
            // Уже закрыт.
        }


        audioContext = null;
    }


    heardSpeech = false;

    visualLevel = 0;


    previousWaveform =
        new Array(
            WAVEFORM_POINTS
        ).fill(0);
}


// =========================================================
// Stop microphone stream
// =========================================================

function stopMediaStream() {
    if (!mediaStream) {
        return;
    }


    mediaStream
        .getTracks()
        .forEach(
            track =>
                track.stop()
        );


    mediaStream = null;
}


// =========================================================
// Transcription
// =========================================================

async function transcribeAudio(
    audioBlob,
    mimeType
) {
    voiceButton.classList.add(
        "processing"
    );


    voiceButton.disabled =
        true;


    input.placeholder =
        "Распознаю речь...";


    try {
        const formData =
            new FormData();


        const extension =
            getFileExtension(
                mimeType
            );


        formData.append(
            "audio",
            audioBlob,
            `voice.${extension}`
        );


        const response =
            await fetch(
                "/api/voice/transcribe",
                {
                    method: "POST",
                    body: formData
                }
            );


        if (!response.ok) {
            let detail =
                "Не удалось распознать речь.";


            try {
                const errorData =
                    await response.json();


                if (
                    errorData.detail
                ) {
                    detail =
                        errorData.detail;
                }

            } catch (_) {
                // Backend может вернуть не JSON.
            }


            throw new Error(
                detail
            );
        }


        const data =
            await response.json();


        input.value =
            data.text;


        resizeInput();


        input.focus();

    } catch (error) {
        console.error(error);


        addMessage(
            "assistant",
            error.message
            ||
            "Ошибка распознавания речи."
        );


        hideWelcome();

    } finally {
        voiceButton.classList.remove(
            "processing"
        );


        voiceButton.disabled =
            false;


        input.placeholder =
            DEFAULT_PLACEHOLDER;
    }
}


// =========================================================
// Form submit
// =========================================================

form.addEventListener(
    "submit",
    async event => {

        event.preventDefault();


        const message =
            input.value.trim();


        if (!message) {
            return;
        }


        input.value = "";


        resizeInput();


        await sendMessage(
            message
        );
    }
);


// =========================================================
// Textarea
// =========================================================

input.addEventListener(
    "input",
    resizeInput
);


input.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter"
            &&
            !event.shiftKey
            &&
            !event.isComposing
        ) {
            event.preventDefault();


            form.requestSubmit();
        }

    }
);


// =========================================================
// Voice button
// =========================================================

voiceButton.addEventListener(
    "click",
    async () => {

        if (isRecording) {
            stopRecording();

            return;
        }


        await startRecording();
    }
);


// =========================================================
// Resize
// =========================================================

window.addEventListener(
    "resize",
    () => {

        if (
            isRecording
            &&
            !waveformContainer.hidden
        ) {
            resizeWaveformCanvas();
        }

    }
);


// =========================================================
// Cleanup
// =========================================================

window.addEventListener(
    "beforeunload",
    () => {

        stopAudioAnalysis();

        stopMediaStream();
    }
);


input.focus();