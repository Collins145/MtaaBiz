(function () {
  const compactKey = "mtaabiz-dashboard-compact";
  const orderKey = "mtaabiz-dashboard-order";
  const settingsForm = document.getElementById("dashboard-settings-form");
  const settingsStatus = document.getElementById("dashboard-settings-status");
  const compactControl = document.getElementById("compact-inbox");
  const orderControl = document.getElementById("message-order");
  let compact = false;
  let order = "newest";

  try {
    compact = localStorage.getItem(compactKey) === "true";
    order = localStorage.getItem(orderKey) === "oldest" ? "oldest" : "newest";
  } catch (error) {
    if (settingsStatus) {
      settingsStatus.textContent = "Your browser could not load saved preferences.";
    }
  }

  if (compactControl && orderControl) {
    compactControl.checked = compact;
    orderControl.value = order;
  }

  const tableBody = document.getElementById("contact-table-body");
  if (tableBody) {
    document.body.classList.toggle("contacts-compact", compact);
    const contactRows = Array.from(tableBody.querySelectorAll("[data-contact-row]"));
    contactRows.sort(function (first, second) {
      const difference = Number(first.dataset.contactId) - Number(second.dataset.contactId);
      return order === "oldest" ? difference : -difference;
    });
    contactRows.forEach(function (row) {
      tableBody.appendChild(row);
    });

    const contactSearch = document.getElementById("contact-search");
    const visibleMessageCount = document.getElementById("visible-message-count");
    const searchEmptyState = document.getElementById("contacts-search-empty");

    contactSearch.addEventListener("input", function () {
      const query = this.value.trim().toLowerCase();
      let visibleCount = 0;

      contactRows.forEach(function (row) {
        const matches = row.textContent.toLowerCase().includes(query);
        row.hidden = !matches;
        if (matches) visibleCount += 1;
      });

      visibleMessageCount.textContent = visibleCount;
      searchEmptyState.hidden = visibleCount > 0 || contactRows.length === 0;
    });
  }

  if (settingsForm) {
    settingsForm.addEventListener("submit", function (event) {
      event.preventDefault();
      try {
        localStorage.setItem(compactKey, String(compactControl.checked));
        localStorage.setItem(orderKey, orderControl.value);
        settingsStatus.textContent = "Preferences saved in this browser.";
      } catch (error) {
        settingsStatus.textContent = "Preferences could not be saved. Check your browser storage settings and try again.";
      }
    });

    document.getElementById("reset-dashboard-settings").addEventListener("click", function () {
      compactControl.checked = false;
      orderControl.value = "newest";
      settingsForm.requestSubmit();
    });
  }
})();
