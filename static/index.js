const searchForm = document.getElementById("shiftSearch");
const slots = searchForm.querySelector(".slots");
const hint = slots.querySelector(".hint");
const order = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

// Hourly choices from 6 AM to 10 PM, shown in 12-hour time.
function timeOptions(selected) {
  let html = "";
  for (let h = 6; h <= 22; h++) {
    const value = `${String(h).padStart(2, "0")}:00`;
    const label = `${h % 12 || 12}:00 ${h < 12 ? "AM" : "PM"}`;
    html += `<option value="${value}"${value === selected ? " selected" : ""}>${label}</option>`;
  }
  return html;
}

// Picking a day adds a "from / to" row for it; unpicking removes it.
searchForm.querySelectorAll('input[name="day"]').forEach((box) => {
  box.addEventListener("change", () => {
    const day = box.value;
    if (box.checked) {
      const row = document.createElement("div");
      row.className = "slot";
      row.dataset.day = day;
      row.innerHTML = `
        <strong>${box.nextElementSibling.textContent}</strong>
        <select name="start_${day}" aria-label="${day} start">${timeOptions("09:00")}</select>
        <span>to</span>
        <select name="end_${day}" aria-label="${day} end">${timeOptions("17:00")}</select>`;
      // Keep rows in Sun–Sat order however the days were clicked.
      const later = [...slots.querySelectorAll(".slot")].find(
        (r) => order.indexOf(r.dataset.day) > order.indexOf(day)
      );
      slots.insertBefore(row, later || null);
    } else {
      slots.querySelector(`.slot[data-day="${day}"]`)?.remove();
    }
    hint.hidden = slots.querySelector(".slot") !== null;
  });
});

// The form posts to /match on its own. This only stops an empty search and
// shows a waiting message, since ranking with Claude takes a few seconds.
searchForm.addEventListener("submit", (e) => {
  const message = document.querySelector(".message");
  if (!searchForm.querySelector('input[name="day"]:checked')) {
    e.preventDefault();
    message.textContent = "Pick at least one day you're free.";
    return;
  }
  message.textContent = "Finding shifts that fit you...";
  searchForm.querySelector('button[type="submit"]').disabled = true;
});

// Coming back with the browser's Back button can restore the page as it was left,
// with the button still disabled, so reset it.
window.addEventListener("pageshow", () => {
  searchForm.querySelector('button[type="submit"]').disabled = false;
  document.querySelector(".message").textContent = "";
});
