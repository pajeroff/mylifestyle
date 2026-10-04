(function() {
  const tg = window.Telegram ? Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
    // Apply theme
    if (tg.themeParams) {
      const root = document.documentElement;
      if (tg.themeParams.bg_color) root.style.setProperty("--tg-bg", tg.themeParams.bg_color);
      if (tg.themeParams.text_color) root.style.setProperty("--tg-text", tg.themeParams.text_color);
      if (tg.themeParams.hint_color) root.style.setProperty("--tg-hint", tg.themeParams.hint_color);
      if (tg.themeParams.button_color) root.style.setProperty("--tg-accent", tg.themeParams.button_color);
      if (tg.themeParams.secondary_bg_color) root.style.setProperty("--tg-secondary-bg", tg.themeParams.secondary_bg_color);
    }
    tg.setHeaderColor(tg.themeParams?.bg_color || "#ffffff");
    tg.BackButton.hide();
  }

  const state = {
    route: "dashboard",
    txType: "expense",
    catType: "expense",
    period: "week",
    statsPeriod: "week",
    selectedCategory: null,
    categories: { expense: [], income: [] },
    summary: null,
    recent: [],
    budgets: [],
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function toast(msg, ms = 2000) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), ms);
  }

  // ----- Navigation -----
  function switchTab(route) {
    state.route = route;
    $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.route === route));
    $$(".page").forEach(p => p.classList.toggle("active", p.id === "page-" + route));
    if (tg) {
      if (route !== "dashboard") tg.BackButton.show();
      else tg.BackButton.hide();
    }
    if (route === "dashboard") loadDashboard();
    else if (route === "add") loadAddPage();
    else if (route === "stats") loadStats();
    else if (route === "budget") loadBudgets();
    else if (route === "categories") loadCategoriesPage();
    window.scrollTo(0, 0);
  }

  $$(".tab").forEach(btn => btn.addEventListener("click", () => switchTab(btn.dataset.route)));
  if (tg) tg.BackButton.onClick(() => switchTab("dashboard"));

  // ----- Dashboard -----
  async function loadDashboard() {
    $("#headerSubtitle").textContent = "Обзор финансов";
    try {
      const [summary, txs] = await Promise.all([
        API.summary(state.period),
        API.transactions(state.period)
      ]);
      state.summary = summary;
      state.recent = txs;

      $("#balanceAmount").textContent = API.formatMoney(summary.balance);
      $("#incomeTotal").textContent = API.formatMoney(summary.income);
      $("#expenseTotal").textContent = API.formatMoney(summary.expense);

      const list = $("#recentList");
      if (!txs.length) {
        list.innerHTML = '<div class="empty">Операций пока нет.<br>Нажми «➕ Добавить» чтобы начать.</div>';
      } else {
        list.innerHTML = txs.slice(0, 15).map(txItem).join("");
        list.querySelectorAll(".tx-item").forEach(el => {
          el.addEventListener("click", () => {
            const tx = txs.find(t => t.id == el.dataset.id);
            const label = tx ? (tx.category_name + (tx.comment ? " — " + tx.comment : "")) : "эту операцию";
            if (confirm(`Удалить операцию «${label}»?`)) {
              API.deleteTransaction(el.dataset.id).then(() => {
                toast("Удалено");
                loadDashboard();
              });
            }
          });
        });
      }

      $$(".period-switch .period-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.period === state.period);
      });
    } catch (e) {
      console.error(e);
      toast("Ошибка загрузки");
    }
  }

  function txItem(tx) {
    const emoji = tx.type === "income" ? "💰" : "💸";
    const cls = tx.type === "income" ? "income" : "expense";
    const sign = tx.type === "income" ? "+" : "−";
    const d = new Date(tx.date);
    const dateStr = d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
    return `<div class="tx-item" data-id="${tx.id}">
      <div class="tx-icon">${emoji}</div>
      <div class="tx-info">
        <div class="tx-name">${escapeHtml(tx.category_name || "—")}</div>
        <div class="tx-sub">${dateStr}${tx.comment ? " · " + escapeHtml(tx.comment) : ""}</div>
      </div>
      <div class="tx-amount ${cls}">${sign}${API.formatMoney(tx.amount)}</div>
    </div>`;
  }

  $$(".period-switch").forEach(group => {
    group.addEventListener("click", (e) => {
      if (e.target.classList.contains("period-btn")) {
        if (e.target.dataset.period !== undefined) {
          state.period = e.target.dataset.period;
          $$(".period-switch .period-btn").forEach(b => {
            if (b.dataset.period) b.classList.toggle("active", b.dataset.period === state.period);
          });
          loadDashboard();
        } else if (e.target.dataset.statsPeriod !== undefined) {
          state.statsPeriod = e.target.dataset.statsPeriod;
          $$(".period-switch .period-btn").forEach(b => {
            if (b.dataset.statsPeriod) b.classList.toggle("active", b.dataset.statsPeriod === state.statsPeriod);
          });
          loadStats();
        }
      }
    });
  });

  // ----- Add page -----
  async function loadAddPage() {
    $("#headerSubtitle").textContent = "Новая операция";
    $("#addDate").value = new Date().toISOString().slice(0, 10);
    $("#addAmount").value = "";
    $("#addComment").value = "";
    state.selectedCategory = null;
    await loadCats();
    renderCatGrid();
    setupTypeSwitch();
  }

  async function loadCats() {
    state.categories.expense = await API.categories("expense");
    state.categories.income = await API.categories("income");
  }

  function setupTypeSwitch() {
    $$(".type-btn[data-type]").forEach(b => {
      b.classList.toggle("active", b.dataset.type === state.txType);
    });
  }

  function renderCatGrid() {
    const cats = state.categories[state.txType] || [];
    const grid = $("#catGrid");
    grid.innerHTML = cats.map(c =>
      `<div class="cat-chip${state.selectedCategory === c.id ? " selected" : ""}" data-cat="${c.id}">${escapeHtml(c.name)}</div>`
    ).join("");
    grid.querySelectorAll(".cat-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        state.selectedCategory = parseInt(chip.dataset.cat);
        renderCatGrid();
      });
    });
  }

  $$(".type-btn[data-type]").forEach(btn => {
    btn.addEventListener("click", async () => {
      state.txType = btn.dataset.type;
      state.selectedCategory = null;
      setupTypeSwitch();
      renderCatGrid();
    });
  });

  $("#saveTxBtn").addEventListener("click", async () => {
    const amount = parseFloat($("#addAmount").value.replace(",", "."));
    if (!amount || amount <= 0) return toast("Введите сумму");
    if (!state.selectedCategory) return toast("Выберите категорию");
    try {
      await API.addTransaction({
        amount,
        category_id: state.selectedCategory,
        type: state.txType,
        comment: $("#addComment").value.trim(),
        date: $("#addDate").value
      });
      toast("✅ Сохранено");
      switchTab("dashboard");
    } catch (e) {
      toast("Ошибка :(");
      console.error(e);
    }
  });

  // Voice input via Web Speech API (works in Telegram Mini Apps in most cases)
  $("#voiceBtn").addEventListener("click", () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      toast("Голосовой ввод не поддерживается");
      return;
    }
    const rec = new SR();
    rec.lang = "ru-RU";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    $("#voiceStatus").textContent = "🎙️ Слушаю...";
    rec.start();
    rec.onresult = async (e) => {
      const text = e.results[0][0].transcript;
      $("#voiceStatus").textContent = "Распознано: " + text;
      try {
        // Parse locally — very simple heuristic matching
        const amountMatch = text.match(/(\d+(?:[.,]\d+)?)/);
        if (!amountMatch) return toast("Не распознал сумму");
        const amount = parseFloat(amountMatch[1].replace(",", "."));
        $("#addAmount").value = amount;

        const incomeWords = ["пришло", "получил", "зарплата", "зп", "доход", "заработал", "пополнение"];
        const isIncome = incomeWords.some(w => text.toLowerCase().includes(w));
        state.txType = isIncome ? "income" : "expense";
        setupTypeSwitch();
        await loadCats();

        // Guess category by keyword match
        const cats = state.categories[state.txType];
        let matched = null;
        for (const c of cats) {
          if (text.toLowerCase().includes(c.name.toLowerCase())) { matched = c; break; }
        }
        if (matched) {
          state.selectedCategory = matched.id;
        }
        renderCatGrid();
        $("#addComment").value = text.replace(amountMatch[0], "").trim().slice(0, 200);
        toast("Определил сумму и категорию");
      } catch (err) {
        console.error(err);
        toast("Не удалось распарсить");
      }
    };
    rec.onerror = () => { $("#voiceStatus").textContent = "Ошибка распознавания"; };
    rec.onend = () => { setTimeout(() => { $("#voiceStatus").textContent = ""; }, 3000); };
  });

  // ----- Stats page -----
  async function loadStats() {
    $("#headerSubtitle").textContent = "Аналитика";
    try {
      const summary = await API.summary(state.statsPeriod);
      state.summary = summary;

      $("#stIncome").textContent = API.formatMoney(summary.income);
      $("#stExpense").textContent = API.formatMoney(summary.expense);

      const setDelta = (el, cur, prev, invertSign) => {
        const e = $(el);
        if (prev === 0 && cur === 0) { e.textContent = "—"; e.className = "summary-delta"; return; }
        if (prev === 0) { e.textContent = "↑ Новый период"; e.className = "summary-delta up"; return; }
        const diff = cur - prev;
        const pct = (diff / prev) * 100;
        const up = diff > 0;
        e.textContent = (up ? "↑ " : "↓ ") + Math.abs(pct).toFixed(0) + "% к прошлому";
        // for expense, up is bad (red); for income, up is good (green)
        const goodUp = !invertSign ? up : !up;
        e.className = "summary-delta " + (goodUp ? "up" : "down");
      };
      setDelta("#stIncomeDelta", summary.income, summary.prev_income, false);
      setDelta("#stExpenseDelta", summary.expense, summary.prev_expense, true);

      Charts.drawPie("pieChart", summary.by_category);
      $("#pieLegend").innerHTML = Charts.renderLegend(summary.by_category);
      Charts.drawLine("lineChart", summary.daily);

      // Compare box
      $("#compareBox").innerHTML = `
        <div class="compare-row"><span>Доход</span><b>${API.formatMoney(summary.income)}</b></div>
        <div class="compare-row"><span>Прошлый период</span><span>${API.formatMoney(summary.prev_income)}</span></div>
        <div class="compare-row"><span>Расход</span><b>${API.formatMoney(summary.expense)}</b></div>
        <div class="compare-row"><span>Прошлый период</span><span>${API.formatMoney(summary.prev_expense)}</span></div>
        <div class="compare-row"><span>Баланс</span><b>${API.formatMoney(summary.balance)}</b></div>
      `;

      // set active period
      $$(".period-switch .period-btn").forEach(b => {
        if (b.dataset.statsPeriod) b.classList.toggle("active", b.dataset.statsPeriod === state.statsPeriod);
      });
    } catch (e) {
      console.error(e);
      toast("Ошибка загрузки");
    }
  }

  // ----- Budgets -----
  async function loadBudgets() {
    $("#headerSubtitle").textContent = "Бюджеты";
    try {
      const [budgets, cats] = await Promise.all([API.budgets(), API.categories("expense")]);
      state.budgets = budgets;
      state.categories.expense = cats;
      const list = $("#budgetList");
      if (!budgets.length) {
        list.innerHTML = '<div class="empty">Лимиты не установлены.<br>Нажмите кнопку ниже, чтобы добавить.</div>';
      } else {
        list.innerHTML = budgets.map(b => {
          const pct = b.limit_amount > 0 ? (b.spent / b.limit_amount) * 100 : 0;
          const cls = pct >= 100 ? "red" : pct >= 80 ? "yellow" : "green";
          return `<div class="budget-item" data-cat="${b.category_id}">
            <div class="budget-name">
              <span>${escapeHtml(b.category_name)}</span>
              <button class="budget-delete" data-del="${b.category_id}">✕</button>
            </div>
            <div class="budget-bar"><div class="budget-fill ${cls}" style="width:${Math.min(pct, 100)}%"></div></div>
            <div class="budget-meta">
              <span>${API.formatMoney(b.spent)} / ${API.formatMoney(b.limit_amount)}</span>
              <span>${pct.toFixed(0)}%</span>
            </div>
          </div>`;
        }).join("");
        list.querySelectorAll(".budget-delete").forEach(btn => {
          btn.addEventListener("click", async () => {
            if (confirm("Удалить лимит?")) {
              await API.deleteBudget(btn.dataset.del);
              toast("Удалено");
              loadBudgets();
            }
          });
        });
      }

      // Populate modal select with categories not yet having budgets
      const sel = $("#budgetCat");
      const existing = new Set(budgets.map(b => b.category_id));
      const avail = cats.filter(c => !existing.has(c.id));
      sel.innerHTML = avail.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
      $("#budgetLimit").value = "";
    } catch (e) {
      console.error(e);
    }
  }

  const modal = $("#budgetModal");
  $("#addBudgetBtn").addEventListener("click", () => {
    if (!$("#budgetCat").options.length) return toast("Для всех категорий уже установлены лимиты");
    modal.classList.remove("hidden");
  });
  $("#budgetCancel").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });
  $("#budgetSave").addEventListener("click", async () => {
    const catId = parseInt($("#budgetCat").value);
    const limit = parseFloat($("#budgetLimit").value.replace(",", "."));
    if (!limit || limit <= 0) return toast("Введите сумму");
    try {
      await API.setBudget(catId, limit);
      modal.classList.add("hidden");
      toast("✅ Лимит сохранён");
      loadBudgets();
    } catch (e) { toast("Ошибка"); }
  });

  // ----- Categories page -----
  async function loadCategoriesPage() {
    $("#headerSubtitle").textContent = "Категории";
    renderCatTypeSwitch();
    await renderCatList();
  }

  function renderCatTypeSwitch() {
    $$(".type-btn[data-cat-type]").forEach(b => {
      b.classList.toggle("active", b.dataset.catType === state.catType);
    });
  }

  $$(".type-btn[data-cat-type]").forEach(btn => {
    btn.addEventListener("click", () => {
      state.catType = btn.dataset.catType;
      renderCatTypeSwitch();
      renderCatList();
    });
  });

  async function renderCatList() {
    const cats = await API.categories(state.catType);
    const list = $("#catList");
    list.innerHTML = cats.map(c => `
      <div class="cat-list-item">
        <span>${escapeHtml(c.name)}</span>
        ${c.is_default ? '<span class="cat-badge">стандартная</span>' : '<span class="cat-badge">пользовательская</span>'}
      </div>
    `).join("");
  }

  $("#addCatBtn").addEventListener("click", async () => {
    const name = $("#newCatName").value.trim();
    if (!name) return toast("Введите название");
    try {
      await API.addCategory(name, state.catType);
      $("#newCatName").value = "";
      toast("✅ Добавлено");
      renderCatList();
    } catch (e) { toast("Ошибка или уже существует"); }
  });

  function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/[&<>"']/g, ch => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[ch]);
  }

  // Init
  loadDashboard().catch(console.error);
})();
