// Placeholder handler: replace with a real call to your backend.
document.querySelectorAll(".card form").forEach((form) => {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const role = form.dataset.role;
    const email = form.querySelector('input[name="email"]').value;
    const message = form.querySelector(".message");

    message.textContent = `Signing in ${email} as ${role}...`;

    // Example:
    // fetch("/api/login", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({ role, email, password: form.password.value }),
    // });
  });
});

// Sign-up popups: open from the links, close with the X, Esc, or a click on the backdrop.
document.querySelectorAll("[data-opens]").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById(link.dataset.opens).showModal();
  });
});

document.querySelectorAll("dialog.modal").forEach((dialog) => {
  dialog.querySelector(".close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => {
    const box = dialog.getBoundingClientRect();
    const outside = e.clientX < box.left || e.clientX > box.right ||
                    e.clientY < box.top || e.clientY > box.bottom;
    if (outside) dialog.close();
  });

  // Placeholder handler: replace with a real call to your backend.
  const form = dialog.querySelector("form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = form.querySelector('input[name="email"]').value;
    form.querySelector(".message").textContent =
      `Creating ${form.dataset.role} account for ${email}...`;
  });
});
