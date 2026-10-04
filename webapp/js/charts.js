// Lightweight chart helpers (no external libs, draws on <canvas>)
const Charts = (() => {
  const COLORS = [
    "#007aff", "#ff9500", "#34c759", "#ff3b30", "#af52de",
    "#ff2d55", "#5ac8fa", "#ffcc00", "#8e8e93", "#5856d6",
    "#30d158", "#ff6482", "#64d2ff", "#bf5af2", "#ffd60a"
  ];

  function colorFor(i) { return COLORS[i % COLORS.length]; }

  // Pie/donut chart
  function drawPie(canvasId, items) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 300;
    const h = 220;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.height = h + "px";
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    if (!items || items.length === 0) {
      ctx.fillStyle = "#8e8e93";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Нет данных", w / 2, h / 2);
      return;
    }

    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) / 2 - 10;
    const innerR = r * 0.6;

    const total = items.reduce((s, i) => s + i.total, 0);
    let start = -Math.PI / 2;

    items.forEach((item, i) => {
      const angle = (item.total / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = colorFor(i);
      ctx.fill();
      start += angle;
    });

    // Donut hole
    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";

    // Center text
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--tg-text").trim() || "#000";
    ctx.font = "bold 18px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(total.toLocaleString("ru-RU", { maximumFractionDigits: 0 }), cx, cy - 8);
    ctx.font = "11px sans-serif";
    ctx.fillStyle = "#8e8e93";
    ctx.fillText("всего", cx, cy + 12);
  }

  // Line / bar chart (daily totals)
  function drawLine(canvasId, points, periodLabel) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 300;
    const h = 200;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.height = h + "px";
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const textColor = getComputedStyle(document.documentElement).getPropertyValue("--tg-text").trim() || "#000";
    const hintColor = "#8e8e93";
    const accent = "#ff3b30";
    const padL = 40, padR = 10, padT = 14, padB = 24;
    const cw = w - padL - padR;
    const ch = h - padT - padB;

    if (!points || points.length === 0) {
      ctx.fillStyle = hintColor;
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Нет данных", w / 2, h / 2);
      return;
    }

    const maxV = Math.max(...points.map(p => p.total), 1);
    const n = points.length;

    // Grid lines (3 lines)
    ctx.strokeStyle = "rgba(128,128,128,0.15)";
    ctx.lineWidth = 1;
    ctx.fillStyle = hintColor;
    ctx.font = "10px sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (let i = 0; i <= 3; i++) {
      const y = padT + ch - (ch * i / 3);
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(w - padR, y);
      ctx.stroke();
      const val = Math.round(maxV * i / 3);
      ctx.fillText(val.toLocaleString("ru-RU"), padL - 4, y);
    }

    // Bars / filled area
    const barW = Math.max(6, Math.min(28, cw / n) - 4);
    const step = cw / Math.max(n - 1, 1);

    // Area fill
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = padL + (n === 1 ? cw / 2 : step * i);
      const y = padT + ch - (p.total / maxV) * ch;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    const lastX = padL + (n === 1 ? cw / 2 : step * (n - 1));
    const firstX = padL;
    ctx.lineTo(lastX, padT + ch);
    ctx.lineTo(firstX, padT + ch);
    ctx.closePath();
    ctx.fillStyle = "rgba(255,59,48,0.15)";
    ctx.fill();

    // Line on top
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = padL + (n === 1 ? cw / 2 : step * i);
      const y = padT + ch - (p.total / maxV) * ch;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = accent;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dots + bars
    ctx.fillStyle = accent;
    points.forEach((p, i) => {
      const x = padL + (n === 1 ? cw / 2 : step * i);
      const y = padT + ch - (p.total / maxV) * ch;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // X labels — show a few dates
    ctx.fillStyle = hintColor;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.font = "10px sans-serif";
    const labelStep = Math.max(1, Math.ceil(n / 6));
    points.forEach((p, i) => {
      if (i % labelStep !== 0 && i !== n - 1) return;
      const x = padL + (n === 1 ? cw / 2 : step * i);
      const d = new Date(p.date);
      const label = d.getDate() + "." + String(d.getMonth() + 1).padStart(2, "0");
      ctx.fillText(label, x, h - padB + 6);
    });
  }

  function renderLegend(items) {
    return items.map((it, i) => {
      const pct = it.total / items.reduce((s, x) => s + x.total, 0) * 100;
      return `<div class="legend-item">
        <span class="legend-color" style="background:${colorFor(i)}"></span>
        ${it.name}: ${it.total.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} (${pct.toFixed(0)}%)
      </div>`;
    }).join("");
  }

  return { drawPie, drawLine, renderLegend, colorFor };
})();
