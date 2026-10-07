/* AVGO 每日追踪 — 归档按日期筛选（原生 JS，无依赖） */
(function () {
  var input = document.getElementById("archive-filter");
  var clearBtn = document.getElementById("archive-clear");
  var section = document.getElementById("archive");
  var empty = document.getElementById("archive-empty");
  if (!input || !section) return;

  function applyFilter() {
    var q = (input.value || "").trim();
    var visible = 0;
    var cards = section.querySelectorAll(".archive-card");
    for (var i = 0; i < cards.length; i++) {
      var hit = !q || (cards[i].getAttribute("data-date") || "").indexOf(q) !== -1;
      cards[i].style.display = hit ? "" : "none";
      if (hit) visible++;
    }
    /* 按月折叠组：筛选时有命中的组自动展开并显示，无命中的组隐藏；
       清空筛选时恢复默认折叠状态 */
    var groups = section.querySelectorAll("details.archive-month");
    for (var j = 0; j < groups.length; j++) {
      var g = groups[j];
      var anyHit = false;
      var gc = g.querySelectorAll(".archive-card");
      for (var k = 0; k < gc.length; k++) {
        if (gc[k].style.display !== "none") { anyHit = true; break; }
      }
      if (!q) {
        g.style.display = "";
        g.open = false;
      } else {
        g.style.display = anyHit ? "" : "none";
        if (anyHit) g.open = true;
      }
    }
    if (empty) empty.hidden = visible > 0;
  }

  input.addEventListener("input", applyFilter);
  /* type="date" 原生支持日期选择器与键盘输入，无需 focus/blur 切换 hack */
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      input.value = "";
      applyFilter();
      input.focus();
    });
  }
})();

/* AVGO 每日追踪 — 访问计数（Abacus，6 秒超时兜底，失败显示 —） */
(function () {
  try {
    var pvEl = document.getElementById("visit-count");
    var uvEl = document.getElementById("visitor-count");
    if (!pvEl || !uvEl) return;
    var host = location.hostname.replace(/[^a-z0-9-]/gi, "-").toLowerCase();
    var base = "https://abacus.jasoncameron.dev";
    var show = function (el, d) {
      el.textContent = (d && typeof d.value === "number") ? d.value.toLocaleString("en-US") : "—";
    };
    /* 带超时的 fetch：国内访问第三方计数服务可能很慢，6 秒未返回直接放弃 */
    function timedGetJson(url) {
      var ctrl = ("AbortController" in window) ? new AbortController() : null;
      var timer = null;
      if (ctrl) timer = setTimeout(function () { ctrl.abort(); }, 6000);
      var opts = { cache: "no-store" };
      if (ctrl) opts.signal = ctrl.signal;
      return fetch(url, opts).then(function (r) {
        if (timer) clearTimeout(timer);
        return r.json();
      }, function (err) {
        if (timer) clearTimeout(timer);
        throw err;
      });
    }
    // 访问量：每次加载 +1
    timedGetJson(base + "/hit/avgo-site/" + encodeURIComponent("pv-" + host))
      .then(function (d) { show(pvEl, d); })
      .catch(function () { pvEl.textContent = "—"; });
    // 访客数：同一浏览器只记一次
    var seen = null;
    try { seen = localStorage.getItem("avgo_uv_v1"); } catch (e) {}
    var uvUrl = seen
      ? base + "/get/avgo-site/" + encodeURIComponent("uv-" + host)
      : base + "/hit/avgo-site/" + encodeURIComponent("uv-" + host);
    timedGetJson(uvUrl)
      .then(function (d) {
        show(uvEl, d);
        if (!seen) { try { localStorage.setItem("avgo_uv_v1", "1"); } catch (e) {} }
      })
      .catch(function () { uvEl.textContent = "—"; });
  } catch (e) {}
})();
