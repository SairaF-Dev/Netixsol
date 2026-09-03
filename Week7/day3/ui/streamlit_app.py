from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


# ============================================================
# PROJECT SETUP
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT / "src"),
)

load_dotenv(
    ROOT / ".env"
)


from sara_agent.runtime import SaraRuntime
from sara_agent.voice import (
    VoicePipeline,
    build_voice_provider,
)


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Sara — Real Estate Voice Assistant",
    page_icon="🏠",
    layout="centered",
)

st.title(
    "🏠 Sara — Real Estate Voice Assistant"
)

st.caption(
    "Verified PostgreSQL + Day 2 RAG • "
    "UrduLish • Text + Live Streaming Voice"
)


# ============================================================
# RUNTIME
# ============================================================

@st.cache_resource
def get_runtime() -> SaraRuntime:
    return SaraRuntime()


@st.cache_resource
def get_voice_provider():
    """
    Existing push-to-talk fallback provider.
    """
    return build_voice_provider()


# ============================================================
# SESSION
# ============================================================

def ensure_session() -> None:

    if "bot" not in st.session_state:
        st.session_state.bot = (
            get_runtime().new_bot(
                response_mode="chat"
            )
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None

    if "last_latency" not in st.session_state:
        st.session_state.last_latency = None


def clear_session() -> None:

    st.session_state.bot.memory.clear()

    st.session_state.messages = []

    st.session_state.last_audio_hash = None
    st.session_state.last_latency = None


# ============================================================
# CHAT HISTORY
# ============================================================

def append_message(
    role: str,
    content: str,
    *,
    audio_bytes: bytes | None = None,
    audio_mime_type: str | None = None,
) -> None:

    message = {
        "role": role,
        "content": content,
    }

    if audio_bytes:

        message["audio_bytes"] = audio_bytes

        message["audio_mime_type"] = (
            audio_mime_type
            or "audio/mpeg"
        )

    st.session_state.messages.append(
        message
    )


def render_history() -> None:

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

            if message.get(
                "audio_bytes"
            ):

                st.audio(
                    message["audio_bytes"],
                    format=message.get(
                        "audio_mime_type",
                        "audio/mpeg",
                    ),
                )


# ============================================================
# OLD PUSH-TO-TALK LATENCY
# ============================================================

def render_latency(
    metrics: dict | None,
) -> None:

    if not metrics:
        return

    st.subheader(
        "⏱ Push-to-talk latency"
    )

    cols = st.columns(4)

    cols[0].metric(
        "STT",
        f"{float(metrics.get('stt_ms', 0)):.0f} ms",
    )

    cols[1].metric(
        "Agent",
        f"{float(metrics.get('agent_ms', 0)):.0f} ms",
    )

    cols[2].metric(
        "TTS",
        f"{float(metrics.get('tts_ms', 0)):.0f} ms",
    )

    total = float(
        metrics.get(
            "total_ms",
            0,
        )
    )

    cols[3].metric(
        "Total",
        f"{total:.0f} ms",
    )

    if total and total < 2000:

        st.success(
            "Latency target met: < 2 seconds ✅"
        )

    elif total:

        st.info(
            "Push-to-talk turn >2s tha. "
            "Live mode mein hum speech-end → "
            "first-audio latency measure karte hain."
        )


# ============================================================
# LIVE STREAMING VOICE COMPONENT
# ============================================================

def build_live_voice_html(
    websocket_url: str,
) -> str:

    html = r"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

body {
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    margin: 0;
    padding: 5px;
}

.container {
    border: 1px solid #dddddd;
    border-radius: 14px;
    padding: 18px;
}

.buttons {
    display: flex;
    gap: 10px;
}

button {
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    cursor: pointer;
    font-size: 14px;
}

#startButton {
    background: #16a34a;
    color: white;
}

#stopButton {
    background: #dc2626;
    color: white;
}

button:disabled {
    opacity: 0.45;
}

.status {
    margin-top: 14px;
    padding: 10px;
    border-radius: 8px;
    background: #f3f4f6;
    color: #111827;
}

.section {
    margin-top: 18px;
}

.label {
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 6px;
}

.box {
    min-height: 35px;
    border-radius: 8px;
    padding: 10px;
    background: #f7f7f7;
    color: #111827;
    white-space: pre-wrap;
}

.turn {
    margin-bottom: 10px;
}

.turn-name {
    font-weight: 700;
}

.latency {
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    gap: 8px;
}

.metric {
    background: #f7f7f7;
    color: #111827;
    padding: 10px;
    border-radius: 8px;
}

.metric-name {
    font-size: 11px;
    opacity: 0.7;
}

.metric-value {
    font-weight: 700;
    margin-top: 4px;
}

.hint {
    margin-top: 14px;
    font-size: 12px;
    opacity: 0.7;
}

</style>

</head>

<body>

<div class="container">

    <div class="buttons">

        <button id="startButton">
            🎙️ Start conversation
        </button>

        <button
            id="stopButton"
            disabled
        >
            ⏹ Stop
        </button>

    </div>


    <div
        id="status"
        class="status"
    >
        Disconnected
    </div>


    <div class="section">

        <div class="label">
            Live transcript
        </div>

        <div
            id="partial"
            class="box"
        >
            —
        </div>

    </div>


    <div class="section">

        <div class="label">
            Conversation
        </div>

        <div
            id="conversation"
            class="box"
        >
            Start conversation press karein.
        </div>

    </div>


    <div class="section">

        <div class="label">
            Latest latency
        </div>

        <div class="latency">

            <div class="metric">

                <div class="metric-name">
                    Agent
                </div>

                <div
                    id="agentLatency"
                    class="metric-value"
                >
                    —
                </div>

            </div>


            <div class="metric">

                <div class="metric-name">
                    First audio
                </div>

                <div
                    id="audioLatency"
                    class="metric-value"
                >
                    —
                </div>

            </div>


            <div class="metric">

                <div class="metric-name">
                    &lt;2 sec target
                </div>

                <div
                    id="target"
                    class="metric-value"
                >
                    —
                </div>

            </div>

        </div>

    </div>


    <div class="hint">

        Headphones recommended for
        interruption / barge-in testing.

    </div>


    <audio
        id="saraAudio"
        autoplay
    ></audio>

</div>


<script>

(() => {

    const WEBSOCKET_URL =
        __WEBSOCKET_URL__;


    const startButton =
        document.getElementById(
            "startButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );

    const status =
        document.getElementById(
            "status"
        );

    const partial =
        document.getElementById(
            "partial"
        );

    const conversation =
        document.getElementById(
            "conversation"
        );

    const agentLatency =
        document.getElementById(
            "agentLatency"
        );

    const audioLatency =
        document.getElementById(
            "audioLatency"
        );

    const target =
        document.getElementById(
            "target"
        );

    const saraAudio =
        document.getElementById(
            "saraAudio"
        );


    let websocket = null;

    let mediaStream = null;

    let audioContext = null;

    let sourceNode = null;

    let processor = null;


    let mediaSource = null;

    let sourceBuffer = null;

    let audioQueue = [];

    let audioURL = null;

    let shouldEndStream = false;

    let conversationStarted = false;


    function updateStatus(text) {

        status.textContent = text;

    }


    function addTurn(
        speaker,
        text
    ) {

        if (!conversationStarted) {

            conversation.innerHTML = "";

            conversationStarted = true;

        }


        const turn =
            document.createElement(
                "div"
            );

        turn.className = "turn";


        const name =
            document.createElement(
                "div"
            );

        name.className =
            "turn-name";

        name.textContent =
            speaker;


        const content =
            document.createElement(
                "div"
            );

        content.textContent =
            text;


        turn.appendChild(
            name
        );

        turn.appendChild(
            content
        );

        conversation.appendChild(
            turn
        );

    }


    function convertFloatToPCM16(
        input
    ) {

        const output =
            new Int16Array(
                input.length
            );


        for (
            let i = 0;
            i < input.length;
            i++
        ) {

            let value =
                Math.max(
                    -1,
                    Math.min(
                        1,
                        input[i]
                    )
                );


            output[i] =
                value < 0
                    ? value * 32768
                    : value * 32767;

        }


        return output;

    }


    function stopSaraAudio() {

        try {

            saraAudio.pause();

        } catch (_) {}


        saraAudio.removeAttribute(
            "src"
        );


        if (audioURL) {

            URL.revokeObjectURL(
                audioURL
            );

            audioURL = null;

        }


        mediaSource = null;

        sourceBuffer = null;

        audioQueue = [];

        shouldEndStream = false;

    }


    function pumpAudioQueue() {

        if (
            !sourceBuffer ||
            sourceBuffer.updating
        ) {
            return;
        }


        if (
            audioQueue.length > 0
        ) {

            const chunk =
                audioQueue.shift();


            try {

                sourceBuffer.appendBuffer(
                    chunk
                );

            } catch (error) {

                updateStatus(
                    "Audio append error: "
                    + error.message
                );

            }


            return;

        }


        if (
            shouldEndStream &&
            mediaSource &&
            mediaSource.readyState
                === "open"
        ) {

            try {

                mediaSource.endOfStream();

            } catch (_) {}


            shouldEndStream = false;

        }

    }


    function startSaraAudioStream(
        mimeType
    ) {

        stopSaraAudio();


        if (
            !window.MediaSource
        ) {

            updateStatus(
                "Browser MediaSource support nahi karta."
            );

            return;

        }


        if (
            !MediaSource.isTypeSupported(
                mimeType
            )
        ) {

            updateStatus(
                mimeType
                + " streaming browser mein unsupported hai."
            );

            return;

        }


        mediaSource =
            new MediaSource();


        audioURL =
            URL.createObjectURL(
                mediaSource
            );


        saraAudio.src =
            audioURL;


        mediaSource.addEventListener(
            "sourceopen",

            () => {

                try {

                    sourceBuffer =
                        mediaSource
                            .addSourceBuffer(
                                mimeType
                            );


                    sourceBuffer.mode =
                        "sequence";


                    sourceBuffer
                        .addEventListener(
                            "updateend",
                            pumpAudioQueue
                        );


                    pumpAudioQueue();


                    saraAudio
                        .play()
                        .catch(
                            () => {}
                        );

                } catch (error) {

                    updateStatus(
                        "TTS playback error: "
                        + error.message
                    );

                }

            },

            {
                once: true
            }
        );

    }


    function enqueueAudio(
        data
    ) {

        audioQueue.push(
            new Uint8Array(
                data
            )
        );


        pumpAudioQueue();

    }


    async function startConversation() {

        startButton.disabled =
            true;


        updateStatus(
            "Microphone permission..."
        );


        try {

            mediaStream =
                await navigator
                    .mediaDevices
                    .getUserMedia({

                        audio: {

                            channelCount: 1,

                            echoCancellation:
                                true,

                            noiseSuppression:
                                true,

                            autoGainControl:
                                true

                        }

                    });


            audioContext =
                new (
                    window.AudioContext
                    ||
                    window.webkitAudioContext
                )();


            await audioContext.resume();


            sourceNode =
                audioContext
                    .createMediaStreamSource(
                        mediaStream
                    );


            processor =
                audioContext
                    .createScriptProcessor(
                        4096,
                        1,
                        1
                    );


            const silentGain =
                audioContext
                    .createGain();


            silentGain.gain.value =
                0;


            sourceNode.connect(
                processor
            );


            processor.connect(
                silentGain
            );


            silentGain.connect(
                audioContext.destination
            );


            websocket =
                new WebSocket(
                    WEBSOCKET_URL
                );


            websocket.binaryType =
                "arraybuffer";


            websocket.onopen =
                () => {

                    websocket.send(
                        JSON.stringify({

                            type:
                                "start",

                            sample_rate:
                                audioContext
                                    .sampleRate,

                            channels:
                                1,

                            encoding:
                                "linear16"

                        })
                    );


                    processor
                        .onaudioprocess =
                        event => {

                            if (
                                !websocket ||
                                websocket
                                    .readyState
                                    !==
                                    WebSocket.OPEN
                            ) {
                                return;
                            }


                            const samples =
                                event
                                    .inputBuffer
                                    .getChannelData(
                                        0
                                    );


                            const pcm =
                                convertFloatToPCM16(
                                    samples
                                );


                            websocket.send(
                                pcm.buffer
                            );

                        };


                    stopButton.disabled =
                        false;


                    updateStatus(
                        "Connecting to Deepgram..."
                    );

                };


            websocket.onmessage =
                event => {


                    /*
                    Binary WebSocket frames
                    are streaming MP3 chunks.
                    */

                    if (
                        typeof event.data
                        !== "string"
                    ) {

                        enqueueAudio(
                            event.data
                        );

                        return;

                    }


                    let message;


                    try {

                        message =
                            JSON.parse(
                                event.data
                            );

                    } catch (_) {

                        return;

                    }


                    switch (
                        message.type
                    ) {


                        case "ready":

                            updateStatus(
                                "Live — Sara sun rahi hai 🎙️"
                            );

                            break;


                        case "stt_connected":

                            updateStatus(
                                "Deepgram Live STT connected"
                            );

                            break;


                        case "speech_started":

                            updateStatus(
                                "Aap bol rahi hain..."
                            );

                            break;


                        case "transcript_partial":

                            partial.textContent =
                                message.transcript
                                || "—";

                            break;


                        case "transcript_segment_final":

                            partial.textContent =
                                message.transcript
                                || partial.textContent;

                            break;


                        case "transcript_final":

                            partial.textContent =
                                "—";


                            addTurn(
                                "You",
                                message.transcript
                                ||
                                message.raw_transcript
                                ||
                                ""
                            );

                            break;


                        case "assistant_text":

                            addTurn(
                                "Sara",
                                message.text
                                || ""
                            );


                            if (
                                typeof
                                message.agent_ms
                                === "number"
                            ) {

                                agentLatency
                                    .textContent =
                                    Math.round(
                                        message.agent_ms
                                    )
                                    + " ms";

                            }

                            break;


                        case "tts_start":

                            startSaraAudioStream(
                                message.mime_type
                                ||
                                "audio/mpeg"
                            );


                            updateStatus(
                                "Sara bol rahi hai..."
                            );

                            break;


                        case "first_audio":

                            if (
                                typeof
                                message
                                    .speech_end_to_first_audio_ms
                                === "number"
                            ) {

                                audioLatency
                                    .textContent =
                                    Math.round(
                                        message
                                            .speech_end_to_first_audio_ms
                                    )
                                    + " ms";

                            }


                            target.textContent =
                                message.under_target
                                ? "< 2 sec ✅"
                                : "≥ 2 sec";

                            break;


                        case "tts_end":

                            shouldEndStream =
                                true;


                            pumpAudioQueue();


                            if (
                                typeof
                                message
                                    .speech_end_to_first_audio_ms
                                === "number"
                            ) {

                                audioLatency
                                    .textContent =
                                    Math.round(
                                        message
                                            .speech_end_to_first_audio_ms
                                    )
                                    + " ms";

                            }


                            target.textContent =
                                message
                                    .under_2s_first_audio_target
                                ? "< 2 sec ✅"
                                : "≥ 2 sec";


                            updateStatus(
                                "Live — Sara sun rahi hai 🎙️"
                            );

                            break;


                        case "interruption":

                            stopSaraAudio();


                            updateStatus(
                                "Barge-in: Sara stopped."
                            );

                            break;


                        case "tts_cancelled":

                            stopSaraAudio();


                            updateStatus(
                                "Sara audio cancelled."
                            );

                            break;


                        case "assistant_superseded":

                            stopSaraAudio();


                            updateStatus(
                                "Old Sara response skipped."
                            );

                            break;


                        case "stt_error":

                        case "tts_error":

                        case "agent_error":

                        case "server_error":

                        case "protocol_error":

                            updateStatus(
                                message.message
                                ||
                                message.type
                            );

                            break;


                        case "session_closed":

                            updateStatus(
                                "Disconnected"
                            );

                            break;

                    }

                };


            websocket.onerror =
                () => {

                    updateStatus(
                        "WebSocket connection failed. "
                        + "FastAPI port 8000 check karein."
                    );

                };


            websocket.onclose =
                () => {

                    updateStatus(
                        "Disconnected"
                    );


                    startButton.disabled =
                        false;


                    stopButton.disabled =
                        true;

                };


        } catch (error) {

            updateStatus(
                "Mic start failed: "
                + error.message
            );


            startButton.disabled =
                false;

        }

    }


    function cleanupMicrophone() {

        if (processor) {

            processor
                .onaudioprocess =
                null;

            try {

                processor.disconnect();

            } catch (_) {}

            processor = null;

        }


        if (sourceNode) {

            try {

                sourceNode.disconnect();

            } catch (_) {}

            sourceNode = null;

        }


        if (mediaStream) {

            mediaStream
                .getTracks()
                .forEach(
                    track =>
                        track.stop()
                );

            mediaStream = null;

        }


        if (audioContext) {

            audioContext
                .close()
                .catch(
                    () => {}
                );

            audioContext = null;

        }

    }


    function stopConversation() {

        stopButton.disabled =
            true;


        if (processor) {

            processor
                .onaudioprocess =
                null;

        }


        if (
            websocket &&
            websocket.readyState
                === WebSocket.OPEN
        ) {

            websocket.send(
                JSON.stringify({

                    type:
                        "stop"

                })
            );

        }


        cleanupMicrophone();


        setTimeout(
            () => {

                if (websocket) {

                    try {

                        websocket.close();

                    } catch (_) {}

                }


                websocket = null;


                stopSaraAudio();


                startButton.disabled =
                    false;


                updateStatus(
                    "Disconnected"
                );

            },

            900
        );

    }


    startButton
        .addEventListener(
            "click",
            startConversation
        );


    stopButton
        .addEventListener(
            "click",
            stopConversation
        );

})();

</script>


</body>

</html>
"""

    return html.replace(
        "__WEBSOCKET_URL__",
        json.dumps(
            websocket_url
        ),
    )


# ============================================================
# STARTUP
# ============================================================

try:

    ensure_session()

except Exception as exc:

    st.error(
        f"Startup configuration error: {exc}"
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.subheader(
        "Conversation"
    )


    if st.button(
        "🧹 Clear memory",
        use_container_width=True,
    ):

        clear_session()

        st.rerun()


    st.write(
        "**Hard requirements**",
        st.session_state
        .bot
        .memory
        .required,
    )


    st.write(
        "**Preferences**",
        st.session_state
        .bot
        .memory
        .preferred,
    )


    st.write(
        "**Exclusions**",
        st.session_state
        .bot
        .memory
        .excluded,
    )


    try:

        rag_status = (
            get_runtime()
            .rag_bridge
            .status()
        )

    except Exception as exc:

        rag_status = {

            "ready":
                False,

            "error":
                exc.__class__.__name__,

        }


    st.write(
        "**RAG**",
        rag_status,
    )


    st.divider()


    st.subheader(
        "Voice configuration"
    )


    stt_provider = os.getenv(
        "VOICE_STT_PROVIDER",
        "faster-whisper",
    ).strip().casefold()


    config_lines = [

        "Fallback STT: "
        + stt_provider,

        "Fallback TTS: "
        + os.getenv(
            "VOICE_TTS_PROVIDER",
            "edge",
        ),

        "Live STT: Deepgram WebSocket",

        "Live TTS: Edge streaming",

        "Deepgram model: "
        + os.getenv(
            "DEEPGRAM_MODEL",
            "nova-3",
        ),

        "Language: "
        + os.getenv(
            "DEEPGRAM_LANGUAGE",
            "ur",
        ),

        "Voice: "
        + os.getenv(
            "EDGE_TTS_VOICE",
            "ur-PK-UzmaNeural",
        ),

    ]


    st.code(
        "\n".join(
            config_lines
        )
    )


# ============================================================
# TABS
# ============================================================

(
    text_tab,
    live_voice_tab,
    fallback_voice_tab,
) = st.tabs(

    [

        "💬 Text chat",

        "🎙️ Live Voice",

        "🎤 Push-to-talk fallback",

    ]

)


# ============================================================
# TEXT CHAT
# ============================================================

with text_tab:

    render_history()


    prompt = st.chat_input(

        "Property requirement likhein...",

        key="text_chat_input",

    )


    if prompt:

        append_message(
            "user",
            prompt,
        )


        with st.chat_message(
            "user"
        ):

            st.markdown(
                prompt
            )


        setter = getattr(

            st.session_state.bot,

            "set_response_mode",

            None,

        )


        if callable(
            setter
        ):

            setter(
                "chat"
            )


        with st.chat_message(
            "assistant"
        ):

            with st.spinner(

                "Verified information check kar rahi hoon..."

            ):

                response = (
                    st.session_state
                    .bot
                    .handle_message(
                        prompt
                    )
                )


            st.markdown(
                response
            )


        append_message(

            "assistant",

            response,

        )


# ============================================================
# LIVE STREAMING VOICE
# ============================================================

with live_voice_tab:

    st.subheader(
        "🎙️ Sara Live Streaming Voice"
    )


    st.write(
        "Mic continuously stream hota hai → "
        "Deepgram Live STT → Sara → "
        "streaming Edge TTS."
    )


    websocket_url = os.getenv(

        "SARA_STREAMING_WS_URL",

        "ws://127.0.0.1:8000/ws/voice",

    ).strip()


    st.caption(
        f"Backend: `{websocket_url}`"
    )


    components.html(

        build_live_voice_html(
            websocket_url
        ),

        height=650,

        scrolling=True,

    )


    st.caption(
        "FastAPI server port 8000 par "
        "running hona chahiye."
    )


# ============================================================
# OLD PUSH-TO-TALK FALLBACK
# ============================================================

with fallback_voice_tab:

    st.write(
        "Ye purana stable fallback hai. "
        "Recording complete hone ke baad "
        "Sara response generate karegi."
    )


    audio_value = st.audio_input(

        "🎤 Sara se baat karein",

        sample_rate=16000,

        key="sara_audio_input",

    )


    if audio_value is not None:

        audio_bytes = (
            audio_value.getvalue()
        )


        audio_hash = (
            hashlib.sha256(
                audio_bytes
            )
            .hexdigest()
        )


        st.caption(
            "Aapki recording"
        )


        st.audio(

            audio_bytes,

            format="audio/wav",

        )


        if (
            audio_hash
            != st.session_state
            .last_audio_hash
        ):

            st.session_state.last_audio_hash = (
                audio_hash
            )


            try:

                provider = (
                    get_voice_provider()
                )


                pipeline = VoicePipeline(

                    st.session_state.bot,

                    provider,

                )


                with st.spinner(

                    "Awaaz samajh kar verified "
                    "response prepare kar rahi hoon..."

                ):

                    result = pipeline.run_turn(

                        audio_bytes,

                        filename="input.wav",

                    )


                user_text = (

                    result.transcript

                    or "_(Awaaz clear nahi thi)_"

                )


                raw_text = (

                    getattr(

                        result,

                        "raw_transcript",

                        "",

                    )

                    or user_text

                )


                append_message(

                    "user",

                    user_text,

                )


                append_message(

                    "assistant",

                    result.response_text,

                    audio_bytes=(
                        result.audio_bytes
                    ),

                    audio_mime_type=(
                        result.audio_mime_type
                    ),

                )


                st.session_state.last_latency = (
                    result.latency_ms
                )


                st.subheader(
                    "📝 Transcript"
                )


                st.write(
                    raw_text
                )


                if (
                    raw_text.strip()
                    != user_text.strip()
                ):

                    st.caption(
                        "Sara-friendly normalized transcript"
                    )

                    st.code(
                        user_text
                    )


                st.subheader(
                    "👩 Sara"
                )


                st.write(
                    result.response_text
                )


                spoken_text = getattr(

                    result,

                    "spoken_text",

                    result.response_text,

                )


                if (
                    spoken_text.strip()
                    != result
                    .response_text
                    .strip()
                ):

                    with st.expander(
                        "🔊 Spoken voice script"
                    ):

                        st.write(
                            spoken_text
                        )


                st.audio(

                    result.audio_bytes,

                    format=(
                        result.audio_mime_type
                    ),

                    autoplay=True,

                )


            except Exception as exc:

                st.error(

                    "Voice turn failed: "
                    f"{exc}\n\n"
                    "Text chat abhi bhi "
                    "use ki ja sakti hai."

                )


    render_latency(
        st.session_state.last_latency
    )


    with st.expander(
        "Conversation history"
    ):

        render_history()