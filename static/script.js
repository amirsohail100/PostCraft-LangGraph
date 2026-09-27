const API_URL = "/api/generate";

const topicInput = document.getElementById("topic");
const genBtn = document.getElementById("genBtn");
const genBtnLabel = document.getElementById("genBtnLabel");
const errorMsg = document.getElementById("errorMsg");

const resultSection = document.getElementById("result");
const verdictBadge = document.getElementById("verdictBadge");
const attemptNote = document.getElementById("attemptNote");
const postTopic = document.getElementById("postTopic");
const postBody = document.getElementById("postBody");
const feedbackBox = document.getElementById("feedbackBox");
const feedbackText = document.getElementById("feedbackText");

function setBusy(isBusy) {
  genBtn.disabled = isBusy;
  topicInput.disabled = isBusy;
  genBtnLabel.textContent = isBusy ? "Writing & reviewing..." : "Generate post";
}

async function generate() {
  const topic = topicInput.value.trim();
  if (!topic) {
    errorMsg.textContent = "Pehle ek topic likho.";
    return;
  }

  errorMsg.textContent = "";
  resultSection.hidden = true;
  setBusy(true);

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);

    if (data.is_approved) {
      verdictBadge.textContent = "APPROVED";
      verdictBadge.className = "verdict-badge approved";
      attemptNote.textContent = `Passed review on attempt ${data.attempt} of 3`;
      feedbackBox.hidden = true;
    } else {
      verdictBadge.textContent = "MAX ATTEMPTS REACHED";
      verdictBadge.className = "verdict-badge rejected";
      attemptNote.textContent = `Best draft after ${data.attempt} attempts`;
      feedbackText.textContent = data.reviewer_feedback;
      feedbackBox.hidden = false;
    }

    postTopic.textContent = topic;
    postBody.textContent = data.draft;
    resultSection.hidden = false;
  } catch (err) {
    errorMsg.textContent = `Error: ${err.message}`;
  } finally {
    setBusy(false);
  }
}

genBtn.addEventListener("click", generate);
topicInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") generate();
});
