"use strict";

const canvas = document.getElementById("waterfall");
const context = canvas.getContext("2d", { alpha: false });
const startButton = document.getElementById("start");
const rowRate = document.getElementById("row-rate");
const statusText = document.getElementById("status");
const stateLight = document.getElementById("state-light");
const idleMessage = document.getElementById("idle-message");
const compassFace = document.getElementById("compass-face");
const compassReading = document.getElementById("compass-reading");

let socket;
let fftSize = 1024;
let minimumLevel = -115;
let maximumLevel = -45;
let palette = buildPalette(["#05070d", "#132d46", "#146c70", "#f4d35e", "#ee6c4d"]);
let reconnectTimer;
let compassHeading;
let compassRotation = 0;

function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/`);
    socket.binaryType = "arraybuffer";
    setStatus("Connecting", false);

    socket.addEventListener("open", () => {
        socket.send("SERVER DE CLIENT client=cbed type=receiver");
    });
    socket.addEventListener("message", receiveMessage);
    socket.addEventListener("close", () => {
        startButton.disabled = true;
        setStatus("Disconnected", false);
        reconnectTimer = window.setTimeout(connect, 2000);
    });
    socket.addEventListener("error", () => socket.close());
}

function receiveMessage(event) {
    if (typeof event.data === "string") {
        if (event.data.startsWith("CLIENT DE SERVER")) {
            return;
        }
        const message = JSON.parse(event.data);
        if (message.type === "config") {
            applyConfig(message.value);
            startButton.disabled = false;
        } else if (message.type === "status") {
            setStatus(message.value, true);
        } else if (message.type === "error") {
            setStatus(message.value, false);
        } else if (message.type === "compass") {
            updateCompass(message.value.heading);
        }
        return;
    }

    const messageType = new Uint8Array(event.data, 0, 1)[0];
    if (messageType === 0x01) {
        const fftData = new Float32Array(event.data.slice(1));
        drawWaterfallRow(fftData);
        idleMessage.classList.add("hidden");
    }
}

function updateCompass(heading) {
    if (!Number.isFinite(heading) || heading < 0 || heading >= 360) {
        return;
    }
    if (compassHeading !== undefined) {
        const change = ((heading - compassHeading + 540) % 360) - 180;
        compassRotation -= change;
    } else {
        compassRotation = -heading;
    }
    compassHeading = heading;
    const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    const direction = directions[Math.round(heading / 45) % directions.length];
    compassFace.style.transform = `rotate(${compassRotation}deg)`;
    compassReading.textContent = `${heading.toFixed(1)}° ${direction}`;
}

function applyConfig(config) {
    fftSize = config.fft_size;
    minimumLevel = config.waterfall_levels.min;
    maximumLevel = config.waterfall_levels.max;
    palette = buildPalette(config.waterfall_colors);
    resizeCanvas();
}

function resizeCanvas() {
    const height = Math.max(1, Math.floor(canvas.getBoundingClientRect().height * window.devicePixelRatio));
    if (canvas.width !== fftSize || canvas.height !== height) {
        canvas.width = fftSize;
        canvas.height = height;
        context.fillStyle = "#05070d";
        context.fillRect(0, 0, canvas.width, canvas.height);
    }
}

function drawWaterfallRow(data) {
    if (data.length !== fftSize) {
        return;
    }
    context.drawImage(canvas, 0, 0, fftSize, canvas.height - 1, 0, 1, fftSize, canvas.height - 1);
    const row = context.createImageData(fftSize, 1);
    for (let index = 0; index < fftSize; index += 1) {
        const normalized = Math.max(0, Math.min(1, (data[index] - minimumLevel) / (maximumLevel - minimumLevel)));
        const color = palette[Math.round(normalized * (palette.length - 1))];
        const offset = index * 4;
        row.data[offset] = color[0];
        row.data[offset + 1] = color[1];
        row.data[offset + 2] = color[2];
        row.data[offset + 3] = 255;
    }
    context.putImageData(row, 0, 0);
}

function buildPalette(stops) {
    const colors = stops.map(hexToRgb);
    return Array.from({ length: 256 }, (_, index) => {
        const position = (index / 255) * (colors.length - 1);
        const left = Math.min(Math.floor(position), colors.length - 2);
        const amount = position - left;
        return colors[left].map((value, channel) => Math.round(value + amount * (colors[left + 1][channel] - value)));
    });
}

function hexToRgb(value) {
    const color = Number.parseInt(value.slice(1), 16);
    return [(color >> 16) & 255, (color >> 8) & 255, color & 255];
}

function setStatus(message, connected) {
    statusText.textContent = message;
    stateLight.classList.toggle("connected", connected);
}

startButton.addEventListener("click", () => {
    const rate = Number.parseInt(rowRate.value, 10);
    if (!Number.isInteger(rate) || rate < 1 || rate > 30) {
        setStatus("Enter a rate from 1 to 30", false);
        rowRate.focus();
        return;
    }
    socket.send(JSON.stringify({ type: "start", value: { rows_per_second: rate } }));
});

new ResizeObserver(resizeCanvas).observe(canvas);
window.addEventListener("beforeunload", () => {
    window.clearTimeout(reconnectTimer);
    socket.close();
});

resizeCanvas();
connect();
