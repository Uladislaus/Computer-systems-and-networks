const yearElement = document.getElementById("year");
const form = document.getElementById("contact-form");
const formMessage = document.getElementById("form-message");

if (yearElement) {
  yearElement.textContent = new Date().getFullYear().toString();
}

if (form && formMessage) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!form.checkValidity()) {
      formMessage.textContent = "Заполни все поля корректно, пожалуйста.";
      return;
    }

    const formData = new FormData(form);
    const name = String(formData.get("name") || "").trim();

    formMessage.textContent = `${name || "Спасибо"}! Сообщение отправлено.`;
    form.reset();
  });
}
