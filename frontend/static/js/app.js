const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");

const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");

const sendButton = document.getElementById("send-button");
const voiceButton = document.getElementById("voice-button");

const composer = document.querySelector(".composer");


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

/*
 * Количество точек линии.
 *
 * Меньше = линия плавнее.
 * Больше = детальнее.
 */
const WAVEFORM_POINTS = 90;


/*
 * Насколько сильно голос
 * визуально увеличивает волну.
 */
const WAVEFORM_GAIN = 2.35;


/*
 * Временное сглаживание.
 *
 * 0 = мгновенная реакция.
 * 1 = очень медленно.
 *
 * 0.38 даёт хороший компромисс:
 * линия реагирует быстро,
 * но не дрожит.
 */
const TEMPORAL_SMOOTHING = 0.38;


/*
 * Сглаживание соседних точек.
 */
const SPATIAL_SMOOTHING = 2;


/*
 * Предыдущий кадр waveform.
 */
let previousWaveform =
    new Array(
        WAVEFORM_POINTS
    ).fill(0);


/*
 * Текущая визуальная громкость.
 */
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
                            message
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
    /*
     * textarea остаётся в layout.
     *
     * Именно поэтому composer
     * не изменяет размеры.
     */
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


    // -----------------------------------------------------
    // Громкость
    // -----------------------------------------------------

    const rms =
        calculateRms(
            dataArray
        );


    const peak =
        calculatePeak(
            dataArray
        );


    /*
     * Ниже этого значения считаем
     * сигнал визуальной тишиной.
     *
     * Это НЕ влияет на автоматическую
     * остановку записи.
     */
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


    /*
     * На подъём реагируем быстрее,
     * на спад немного плавнее.
     */
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


    /*
     * Если действительно тихо —
     * постепенно возвращаем линию
     * в идеальный центр.
     */
    if (
        visualLevel < 0.025
    ) {
        visualLevel = 0;
    }


    // -----------------------------------------------------
    // Получаем форму сигнала
    // -----------------------------------------------------

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


    /*
     * Нормализуем форму текущей волны
     * относительно её пика.
     *
     * Благодаря этому тихая речь
     * тоже визуально заметна.
     */
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


        /*
         * Ограничиваем редкие
         * слишком резкие пики.
         */
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


    /*
     * Сглаживаем соседние точки,
     * чтобы линия не была зубчатой.
     */
    const spatialPoints =
        smoothWaveformPoints(
            rawPoints,
            SPATIAL_SMOOTHING
        );


    // -----------------------------------------------------
    // Temporal smoothing
    // -----------------------------------------------------

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


    // -----------------------------------------------------
    // Draw
    // -----------------------------------------------------

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


    /*
     * Ограничиваем амплитуду,
     * чтобы линия не упиралась
     * в края canvas.
     */
    const safeAmplitude =
        Math.min(
            maxAmplitude,
            height * 0.43
        );


    waveformContext.beginPath();


    /*
     * Рисуем кривую через midpoint.
     *
     * Получается значительно мягче
     * обычных lineTo между точками.
     */
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


        /*
         * Уменьшаем амплитуду
         * возле краёв линии.
         */
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


    /*
     * Хороший баланс между
     * отзывчивостью и детализацией.
     */
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


        /*
         * Рисуем живую waveform.
         */
        drawWaveform(
            dataArray
        );


        /*
         * Определяем громкость
         * отдельно от визуализации.
         */
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


        /*
         * Пользователь говорил,
         * затем молчит 1.8 сек.
         */
        if (
            heardSpeech
            &&
            now - lastSoundAt
            >= SILENCE_DURATION
        ) {
            stopRecording();

            return;
        }


        /*
         * Максимум 30 секунд.
         */
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