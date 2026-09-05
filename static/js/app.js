const form = document.getElementById("ask-form");
const imageInput = document.getElementById("image-input");
const dropZone = document.getElementById("drop-zone");
const previewImg = document.getElementById("preview-img");
const dropLabel = document.getElementById("drop-label");
const questionInput = document.getElementById("question-input");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");

const idleState = document.getElementById("idle-state");
const loadingState = document.getElementById("loading-state");
const loadingText = document.getElementById("loading-text");
const resultState = document.getElementById("result-state");
const askedQuestion = document.getElementById("asked-question");
const answerText = document.getElementById("answer-text");

const audioEl = document.getElementById("answer-audio");
const playBtn = document.getElementById("play-btn");
const playIcon = document.getElementById("play-icon");
const pauseIcon = document.getElementById("pause-icon");
const waveform = document.getElementById("waveform");

const LOADING_MESSAGES = [
  "Looking closely…",
  "Thinking it over…",
  "Finding the words…",
];

let selectedFile = null;

// ---------- Image selection & preview ----------
function handleFile(file) {
  if (!file) return;
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewImg.classList.remove("hidden");
    dropLabel.classList.add("hidden");
  };
  reader.readAsDataURL(file);
}

imageInput.addEventListener("change", () => {
  if (imageInput.files && imageInput.files[0]) {
    handleFile(imageInput.files[0]);
  }
});

["dragenter", "dragover"].forEach((evt) => {
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((evt) => {
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
  });
});

dropZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0];
  if (file) {
    imageInput.files = e.dataTransfer.files;
    handleFile(file);
  }
});

// ---------- Form submit ----------
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  formError.classList.add("hidden");

  if (!selectedFile) {
    showError("Please choose an image first.");
    return;
  }
  const question = questionInput.value.trim();
  if (!question) {
    showError("Please type a question.");
    return;
  }

  setLoading(true);

  const formData = new FormData();
  formData.append("image", selectedFile);
  formData.append("question", question);

  try {
    const res = await fetch("/ask", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    askedQuestion.textContent = `“${data.question}”`;
    answerText.textContent = data.answer;
    audioEl.src = data.audio_url;

    idleState.classList.add("hidden");
    loadingState.classList.add("hidden");
    resultState.classList.remove("hidden");

    resetPlayButton();
  } catch (err) {
    showError(err.message || "Something went wrong. Please try again.");
    idleState.classList.remove("hidden");
    loadingState.classList.add("hidden");
  } finally {
    setLoading(false);
  }
});

function showError(msg) {
  formError.textContent = msg;
  formError.classList.remove("hidden");
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.textContent = isLoading ? "Asking…" : "Ask";
  if (isLoading) {
    idleState.classList.add("hidden");
    resultState.classList.add("hidden");
    loadingText.textContent =
      LOADING_MESSAGES[Math.floor(Math.random() * LOADING_MESSAGES.length)];
    loadingState.classList.remove("hidden");
  }
}

// ---------- Audio playback ----------
playBtn.addEventListener("click", () => {
  if (audioEl.paused) {
    audioEl.play();
  } else {
    audioEl.pause();
  }
});

audioEl.addEventListener("play", () => {
  playIcon.classList.add("hidden");
  pauseIcon.classList.remove("hidden");
  waveform.classList.add("playing");
});

audioEl.addEventListener("pause", resetPlayButton);
audioEl.addEventListener("ended", resetPlayButton);

function resetPlayButton() {
  playIcon.classList.remove("hidden");
  pauseIcon.classList.add("hidden");
  waveform.classList.remove("playing");
}
