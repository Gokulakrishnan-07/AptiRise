/**
 * AptiRise Interactive Game Controller
 * Manages question flow, card transitions, timer, XP celebrations, and level completions.
 */

class GameEngine {
  constructor(options) {
    this.levelId = options.levelId;
    this.collectionSlug = options.collectionSlug;
    this.isDaily = options.isDaily || false;
    this.apiUrl = this.isDaily
      ? "/api/daily-challenge/questions"
      : `/api/game/level/${this.levelId}/questions`;

    this.questions = [];
    this.currentIndex = 0;
    this.selectedOption = null;
    this.timer = null;
    this.timeRemaining = 45;
    this.questionStartTime = Date.now();
    this.isAnswered = false;

    // Session Metrics
    this.correctCount = 0;
    this.wrongCount = 0;
    this.totalScore = 0;
    this.totalTimeTaken = 0;

    // DOM Elements
    this.cardEl = document.getElementById("gameCard");
    this.progressFillEl = document.getElementById("gameProgressFill");
    this.qCounterEl = document.getElementById("qCounter");
    this.timerEl = document.getElementById("timerText");
    this.timerPill = document.getElementById("timerPill");
    this.qTextEl = document.getElementById("questionText");
    this.optionsContainer = document.getElementById("optionsContainer");
    this.submitBtn = document.getElementById("submitAnswerBtn");
    this.nextBtn = document.getElementById("nextQuestionBtn");
    this.solutionContainer = document.getElementById("solutionContainer");
    this.levelUpModal = document.getElementById("levelUpModal");
    this.levelCompleteModal = document.getElementById("levelCompleteModal");

    this.init();
  }

  async init() {
    try {
      const resp = await fetch(this.apiUrl);
      if (!resp.ok) throw new Error("Failed to load questions");
      const data = await resp.json();
      this.questions = data.questions || [];

      if (this.questions.length === 0) {
        this.qTextEl.textContent = "No questions found for this level yet.";
        return;
      }

      this.submitBtn.addEventListener("click", () => this.submitAnswer());
      this.nextBtn.addEventListener("click", () => this.nextQuestion());

      this.renderQuestion(0);
    } catch (e) {
      this.qTextEl.textContent = "Error loading question deck. Please refresh.";
    }
  }

  renderQuestion(index) {
    if (index >= this.questions.length) {
      this.finishLevel();
      return;
    }

    const q = this.questions[index];
    this.currentIndex = index;
    this.isAnswered = false;
    this.selectedOption = null;
    this.questionStartTime = Date.now();

    // Reset controls
    this.submitBtn.style.display = "inline-flex";
    this.submitBtn.disabled = true;
    this.nextBtn.style.display = "none";
    this.solutionContainer.style.display = "none";
    this.solutionContainer.innerHTML = "";

    // Update Counter & Progress
    this.qCounterEl.textContent = `Question ${index + 1} of ${this.questions.length}`;
    const pct = ((index) / this.questions.length) * 100;
    this.progressFillEl.style.width = `${pct}%`;

    // Reset Card Animation
    this.cardEl.classList.remove("slide-out");
    this.cardEl.classList.add("slide-in");
    setTimeout(() => this.cardEl.classList.remove("slide-in"), 300);

    // Text & Options
    this.qTextEl.textContent = q.question_text;
    this.optionsContainer.innerHTML = "";

    q.options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.dataset.label = opt.label;
      btn.innerHTML = `
        <span class="option-letter">${opt.label}</span>
        <span class="option-text">${opt.text}</span>
      `;
      btn.addEventListener("click", () => this.selectOption(opt.label, btn));
      this.optionsContainer.appendChild(btn);
    });

    // Start Timer
    this.startTimer(q.time_limit || 45);
  }

  selectOption(label, buttonEl) {
    if (this.isAnswered) return;

    if (window.soundEngine) {
      window.soundEngine.playTap();
    }

    // Toggle active state
    const allBtns = this.optionsContainer.querySelectorAll(".option-btn");
    allBtns.forEach((b) => b.classList.remove("selected"));

    buttonEl.classList.add("selected");
    this.selectedOption = label;
    this.submitBtn.disabled = false;
  }

  startTimer(seconds) {
    clearInterval(this.timer);
    this.timeRemaining = seconds;
    this.updateTimerDisplay();

    this.timer = setInterval(() => {
      this.timeRemaining--;
      this.updateTimerDisplay();

      if (this.timeRemaining <= 0) {
        clearInterval(this.timer);
        if (!this.isAnswered) {
          this.autoSubmitTimeout();
        }
      }
    }, 1000);
  }

  updateTimerDisplay() {
    const mins = Math.floor(this.timeRemaining / 60);
    const secs = this.timeRemaining % 60;
    this.timerEl.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

    if (this.timeRemaining <= 10) {
      this.timerPill.classList.add("urgent");
    } else {
      this.timerPill.classList.remove("urgent");
    }
  }

  autoSubmitTimeout() {
    this.submitAnswer(true);
  }

  async submitAnswer(isTimeout = false) {
    if (this.isAnswered) return;
    this.isAnswered = true;
    clearInterval(this.timer);

    const timeTaken = Math.max(1, (Date.now() - this.questionStartTime) / 1000);
    this.totalTimeTaken += timeTaken;

    const currentQ = this.questions[this.currentIndex];
    const chosenLabel = isTimeout ? "" : this.selectedOption;

    // Disable all options
    const allBtns = this.optionsContainer.querySelectorAll(".option-btn");
    allBtns.forEach((b) => (b.disabled = true));

    try {
      const resp = await fetch("/api/game/submit-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_id: currentQ.id,
          level_id: this.levelId,
          selected_option_label: chosenLabel,
          time_taken_seconds: parseFloat(timeTaken.toFixed(1)),
        }),
      });

      const res = await resp.json();

      // Audio & Visual Feedback
      if (res.is_correct) {
        this.correctCount++;
        this.totalScore += res.xp_earned;
        if (window.soundEngine) window.soundEngine.playCorrect();

        const pickedBtn = this.optionsContainer.querySelector(`[data-label="${chosenLabel}"]`);
        if (pickedBtn) pickedBtn.classList.add("correct");
      } else {
        this.wrongCount++;
        if (window.soundEngine) window.soundEngine.playWrong();

        if (chosenLabel) {
          const pickedBtn = this.optionsContainer.querySelector(`[data-label="${chosenLabel}"]`);
          if (pickedBtn) pickedBtn.classList.add("wrong");
        }
        // Highlight correct option
        const correctBtn = this.optionsContainer.querySelector(`[data-label="${res.correct_option_label}"]`);
        if (correctBtn) correctBtn.classList.add("correct");
      }

      // Display Explanation & Shortcut
      this.renderSolution(res);

      // Level up celebration check
      if (res.level_up) {
        setTimeout(() => this.triggerLevelUpCelebration(res.new_user_level), 600);
      }

      // Switch buttons
      this.submitBtn.style.display = "none";
      this.nextBtn.style.display = "inline-flex";

      if (this.currentIndex === this.questions.length - 1) {
        this.nextBtn.textContent = "Finish Level →";
      }
    } catch (e) {
      console.error("Submission failed:", e);
    }
  }

  renderSolution(res) {
    this.solutionContainer.style.display = "block";
    this.solutionContainer.className = `solution-box ${res.is_correct ? "correct-box" : "wrong-box"}`;

    let speedBadge = "";
    if (res.speed_bonus > 0) {
      speedBadge = `<span class="badge badge-amber" style="margin-left: 0.5rem;">⚡ Speed Bonus +${res.speed_bonus} XP</span>`;
    }

    this.solutionContainer.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
        <span class="badge ${res.is_correct ? "badge-emerald" : "badge-rose"}">
          ${res.is_correct ? "✓ Correct! +" + res.xp_earned + " XP" : "✗ Incorrect"}
        </span>
        ${speedBadge}
        <span style="font-size: 0.82rem; color: var(--text-tertiary);">${res.time_taken_seconds}s</span>
      </div>

      <div style="font-size: 0.95rem; margin-bottom: 0.5rem;">
        <strong>Correct Answer:</strong> Option ${res.correct_option_label} — ${res.correct_option_text}
      </div>

      ${res.explanation ? `<p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${res.explanation}</p>` : ""}

      ${res.shortcut ? `
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle);">
          <div class="shortcut-badge">💡 Formula & Shortcut</div>
          <p style="font-size: 0.88rem; font-weight: 500;">${res.shortcut}</p>
        </div>
      ` : ""}
    `;
  }

  nextQuestion() {
    this.cardEl.classList.add("slide-out");
    setTimeout(() => {
      this.renderQuestion(this.currentIndex + 1);
    }, 250);
  }

  async finishLevel() {
    this.progressFillEl.style.width = "100%";
    if (window.soundEngine) window.soundEngine.playLevelUp();

    if (this.isDaily) {
      // Daily completion
      try {
        const resp = await fetch("/api/daily-challenge/complete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            correct_count: this.correctCount,
            score: this.totalScore
          })
        });
        const res = await resp.json();
        this.renderCompletionModal(true, res.bonus_xp);
      } catch (e) {}
    } else {
      // Level completion
      try {
        const resp = await fetch("/api/game/complete-level", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            level_id: this.levelId,
            time_taken_seconds: parseFloat(this.totalTimeTaken.toFixed(1)),
            total_score: this.totalScore,
            correct_count: this.correctCount,
            wrong_count: this.wrongCount
          })
        });
        const res = await resp.json();
        this.renderCompletionModal(false, 0, res);
      } catch (e) {}
    }
  }

  renderCompletionModal(isDaily, bonusXp = 0, levelRes = {}) {
    const accuracy = Math.round((this.correctCount / Math.max(1, this.questions.length)) * 100);
    const mins = Math.floor(this.totalTimeTaken / 60);
    const secs = Math.floor(this.totalTimeTaken % 60);
    const timeFormatted = `${mins}m ${secs}s`;

    const totalEarned = this.totalScore + (levelRes.xp_earned ? (levelRes.xp_earned - this.totalScore) : bonusXp);

    document.getElementById("modalScore").textContent = this.totalScore;
    document.getElementById("modalAccuracy").textContent = `${accuracy}%`;
    document.getElementById("modalXpEarned").textContent = `+${totalEarned} XP`;
    document.getElementById("modalTime").textContent = timeFormatted;
    document.getElementById("modalCorrect").textContent = this.correctCount;
    document.getElementById("modalWrong").textContent = this.wrongCount;

    if (levelRes.is_perfect) {
      document.getElementById("perfectBadge").style.display = "inline-flex";
    }

    this.levelCompleteModal.classList.add("active");
  }

  triggerLevelUpCelebration(newLevel) {
    if (window.soundEngine) window.soundEngine.playLevelUp();
    document.getElementById("newLevelNumber").textContent = `Level ${newLevel}`;
    this.levelUpModal.classList.add("active");

    setTimeout(() => {
      this.levelUpModal.classList.remove("active");
    }, 3200);
  }
}

window.GameEngine = GameEngine;
