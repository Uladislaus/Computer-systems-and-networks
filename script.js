const header = document.querySelector(".site-header");
const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelectorAll(".site-nav a");
const form = document.querySelector(".contact-form");
const formNote = document.querySelector(".form-note");

navToggle?.addEventListener("click", () => {
  const isOpen = header?.classList.toggle("is-open") ?? false;
  navToggle.setAttribute("aria-expanded", String(isOpen));
});

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    header.classList.remove("is-open");
    navToggle?.setAttribute("aria-expanded", "false");
  });
});

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (formNote) {
    formNote.hidden = false;
    formNote.textContent = "Спасибо! Заявка готова к отправке после подключения backend.";
  }
});

form?.addEventListener("input", () => {
  if (formNote) {
    formNote.textContent = "";
    formNote.hidden = true;
  }
});
