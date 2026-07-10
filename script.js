const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelector(".nav-links");
const menuLinks = document.querySelectorAll(".nav-links a");

navToggle?.addEventListener("click", () => {
  const isOpen = navLinks.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
});

menuLinks.forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.classList.remove("is-open");
    navToggle?.setAttribute("aria-expanded", "false");
  });
});

const practices = [
  {
    kicker: "Упражнение 1",
    title: "Ассоциативная цепочка",
    text: "Возьмите 5 слов, придумайте к каждому яркий образ и соедините их в одну смешную историю. Через 10 минут восстановите цепочку без записи.",
  },
  {
    kicker: "Упражнение 2",
    title: "Комната воспоминаний",
    text: "Представьте знакомую комнату и разместите в ней важные факты. Пройдите маршрут мысленно и назовите каждый предмет по порядку.",
  },
  {
    kicker: "Упражнение 3",
    title: "Тихое повторение",
    text: "Прочитайте короткий фрагмент, сделайте три спокойных вдоха и повторите смысл своими словами без спешки.",
  },
];

const practiceButtons = document.querySelectorAll(".practice-card");
const practiceDetail = document.querySelector(".practice-detail");

practiceButtons.forEach((button, index) => {
  button.addEventListener("click", () => {
    practiceButtons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");

    const practice = practices[index];
    practiceDetail.innerHTML = `
      <p class="detail-kicker">${practice.kicker}</p>
      <h3>${practice.title}</h3>
      <p>${practice.text}</p>
    `;
  });
});

const sections = document.querySelectorAll("main section[id]");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }

      menuLinks.forEach((link) => {
        link.classList.toggle("is-current", link.getAttribute("href") === `#${entry.target.id}`);
      });
    });
  },
  { rootMargin: "-45% 0px -50% 0px" },
);

sections.forEach((section) => observer.observe(section));

const startForm = document.querySelector(".start-form");
const formMessage = document.querySelector(".form-message");

startForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(startForm);
  const goal = String(form.get("goal") || "").trim();
  const focus = goal || "одну короткую тренировку памяти";

  formMessage.textContent = `Готово: сегодня выделите 10 минут на цель "${focus}".`;
});
