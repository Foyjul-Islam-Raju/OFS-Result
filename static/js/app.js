/* OFS Result System - small progressive enhancements.
   All validation here is a convenience only; the server re-validates. */
(function () {
  "use strict";

  // Sidebar drawer on small screens
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const sidebar = document.querySelector(".sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      if (sidebar.classList.contains("open")) {
        const backdrop = document.createElement("div");
        backdrop.className = "backdrop";
        backdrop.addEventListener("click", function () {
          sidebar.classList.remove("open");
          backdrop.remove();
        });
        document.body.appendChild(backdrop);
      } else {
        document.querySelectorAll(".backdrop").forEach((b) => b.remove());
      }
    });
  }

  // Mark entry: flag out-of-range values and disable the input when absent
  document.querySelectorAll(".mark-input").forEach(function (input) {
    const full = parseFloat(input.dataset.fullMark || "0");
    function check() {
      const raw = input.value.trim();
      if (raw === "") { input.classList.remove("cell-invalid"); return; }
      const value = parseFloat(raw);
      const bad = isNaN(value) || value < 0 || value > full;
      input.classList.toggle("cell-invalid", bad);
      input.setCustomValidity(
        bad ? "Enter a number between 0 and " + full + "." : ""
      );
    }
    input.addEventListener("input", check);
    check();
  });

  document.querySelectorAll(".absent-toggle").forEach(function (box) {
    const cell = box.closest("td");
    const input = cell ? cell.querySelector(".mark-input") : null;
    function sync() {
      if (!input) return;
      input.disabled = box.checked;
      if (box.checked) { input.value = ""; input.classList.remove("cell-invalid"); }
    }
    box.addEventListener("change", sync);
    sync();
  });

  // Keyboard flow: Enter moves down the column like a spreadsheet
  const inputs = Array.from(document.querySelectorAll(".mark-input"));
  inputs.forEach(function (input, index) {
    input.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const columns = parseInt(input.dataset.columns || "0", 10);
      const next = inputs[index + (columns || 1)] || inputs[index + 1];
      if (next) { next.focus(); next.select(); }
    });
  });

  // Confirm destructive actions
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (event) {
      if (!window.confirm(el.dataset.confirm)) event.preventDefault();
    });
  });

  // Dependent class -> section filtering
  const classField = document.querySelector("#id_classroom");
  const sectionField = document.querySelector("#id_section");
  if (classField && sectionField) {
    const options = Array.from(sectionField.options).map(function (option) {
      return { option: option, parent: option.dataset.classroom || "" };
    });
    function filter() {
      const chosen = classField.value;
      sectionField.innerHTML = "";
      options.forEach(function (item) {
        if (!item.parent || !chosen || item.parent === chosen) {
          sectionField.appendChild(item.option);
        }
      });
    }
    classField.addEventListener("change", filter);
  }
})();
