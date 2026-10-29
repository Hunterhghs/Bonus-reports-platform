/* Bonus Reports Platform — catalog filtering (vanilla, no deps) */
(function () {
  "use strict";

  var grid = document.getElementById("card-grid");
  if (!grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll(".card"));
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".filter-tab"));
  var search = document.getElementById("search");
  var count = document.getElementById("result-count");
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".site-nav a"));

  function getParam(name) {
    return new URLSearchParams(window.location.search).get(name) || "";
  }

  function setTab(filter) {
    tabs.forEach(function (t) {
      var active = t.getAttribute("data-filter") === filter;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  function applyFilters() {
    var filter = getParam("type") || "all";
    var query = (search.value || "").trim().toLowerCase();
    var visible = 0;

    cards.forEach(function (card) {
      var typeMatch = filter === "all" || card.getAttribute("data-type") === filter;
      var queryMatch = !query || card.getAttribute("data-search").indexOf(query) !== -1;
      var show = typeMatch && queryMatch;
      card.classList.toggle("hidden", !show);
      if (show) visible += 1;
    });

    if (count) {
      count.textContent = visible === cards.length
        ? cards.length + " projects"
        : visible + " of " + cards.length + " projects";
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      var filter = tab.getAttribute("data-filter");
      var params = new URLSearchParams(window.location.search);
      if (filter === "all") params.delete("type");
      else params.set("type", filter);
      var qs = params.toString();
      history.replaceState(null, "", qs ? "?" + qs : window.location.pathname);
      setTab(filter);
      applyFilters();
    });
  });

  search.addEventListener("input", applyFilters);
  search.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      search.value = "";
      applyFilters();
    }
  });

  navLinks.forEach(function (link) {
    link.addEventListener("click", function (e) {
      var key = link.getAttribute("data-nav");
      if (!key) return;
      e.preventDefault();
      var params = new URLSearchParams(window.location.search);
      if (key === "all") params.delete("type");
      else params.set("type", key);
      var qs = params.toString();
      var dest = "/" + (qs ? "?" + qs : "");
      window.location.href = dest;
    });
  });

  var initial = getParam("type") || "all";
  if (initial !== "all") setTab(initial);
  if (getParam("q")) search.value = getParam("q");
  applyFilters();
})();
