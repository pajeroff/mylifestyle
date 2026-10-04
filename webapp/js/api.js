// API wrapper — attaches Telegram initData to every request
const API = (() => {
  const BASE = "";

  function getInitData() {
    if (window.Telegram && Telegram.WebApp) {
      return Telegram.WebApp.initData || "";
    }
    return "";
  }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const initData = getInitData();
    if (initData) headers["X-Telegram-Init-Data"] = initData;
    const res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    return res.json();
  }

  return {
    getMe: () => request("GET", "/api/me"),
    categories: (type) => request("GET", `/api/categories?type=${type}`),
    addCategory: (name, type) => request("POST", "/api/categories", { name, type }),
    transactions: (period) => request("GET", `/api/transactions?period=${period}`),
    addTransaction: (data) => request("POST", "/api/transactions", data),
    deleteTransaction: (id) => request("DELETE", `/api/transactions/${id}`),
    summary: (period) => request("GET", `/api/summary?period=${period}`),
    budgets: () => request("GET", "/api/budgets"),
    setBudget: (category_id, limit_amount) => request("POST", "/api/budgets", { category_id, limit_amount }),
    deleteBudget: (category_id) => request("DELETE", `/api/budgets/${category_id}`),
    formatMoney(amount, currency = "₽") {
      if (amount == null || isNaN(amount)) return "—";
      const rounded = Math.round(amount * 100) / 100;
      const formatted = rounded.toLocaleString("ru-RU", {
        minimumFractionDigits: rounded % 1 === 0 ? 0 : 2,
        maximumFractionDigits: 2,
      });
      return formatted + " " + currency;
    }
  };
})();
