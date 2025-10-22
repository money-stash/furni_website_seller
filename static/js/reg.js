// Валідація форми реєстрації
document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("form");
  const fullName = document.getElementById("full_name");
  const email = document.getElementById("email");
  const phone = document.getElementById("phone");
  const password = document.getElementById("password");
  const password2 = document.getElementById("password2");
  const terms = document.getElementById("terms");

  // Функція для показу помилки
  function showError(input, message) {
    const formControl = input.parentElement;
    let error = formControl.querySelector(".error-message");

    if (!error) {
      error = document.createElement("div");
      error.className = "error-message text-danger small mt-1";
      formControl.appendChild(error);
    }

    error.textContent = message;
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
  }

  // Функція для показу успіху
  function showSuccess(input) {
    const formControl = input.parentElement;
    const error = formControl.querySelector(".error-message");

    if (error) {
      error.remove();
    }

    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
  }

  // Перевірка повного імені
  function validateFullName() {
    const value = fullName.value.trim();

    if (value === "") {
      showError(fullName, "Повне ім'я обов'язкове");
      return false;
    } else if (value.length < 2) {
      showError(fullName, "Ім'я повинно містити мінімум 2 символи");
      return false;
    } else if (!/^[а-яА-ЯіІїЇєЄґҐa-zA-Z\s'-]+$/.test(value)) {
      showError(fullName, "Ім'я може містити тільки букви");
      return false;
    } else {
      showSuccess(fullName);
      return true;
    }
  }

  // Перевірка email
  function validateEmail() {
    const value = email.value.trim();

    // Email опціональний, але якщо введений - перевіряємо
    if (value === "") {
      email.classList.remove("is-invalid", "is-valid");
      const error = email.parentElement.querySelector(".error-message");
      if (error) error.remove();
      return true;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(value)) {
      showError(email, "Введіть коректну електронну адресу");
      return false;
    } else {
      showSuccess(email);
      return true;
    }
  }

  // Перевірка телефону
  function validatePhone() {
    const value = phone.value.trim();

    if (value === "") {
      showError(phone, "Телефон обов'язковий");
      return false;
    }

    // Видаляємо всі нецифрові символи для перевірки
    const digitsOnly = value.replace(/\D/g, "");

    if (digitsOnly.length < 10) {
      showError(phone, "Введіть коректний номер телефону");
      return false;
    } else {
      showSuccess(phone);
      return true;
    }
  }

  // Перевірка пароля
  function validatePassword() {
    const value = password.value;

    if (value === "") {
      showError(password, "Пароль обов'язковий");
      return false;
    } else if (value.length < 8) {
      showError(password, "Пароль повинен містити мінімум 8 символів");
      return false;
    } else if (!/[A-Z]/.test(value)) {
      showError(password, "Пароль повинен містити хоча б одну велику літеру");
      return false;
    } else if (!/[a-z]/.test(value)) {
      showError(password, "Пароль повинен містити хоча б одну малу літеру");
      return false;
    } else if (!/[0-9]/.test(value)) {
      showError(password, "Пароль повинен містити хоча б одну цифру");
      return false;
    } else {
      showSuccess(password);
      return true;
    }
  }

  // Перевірка збігу паролів
  function validatePassword2() {
    const value = password2.value;
    const passwordValue = password.value;

    if (value === "") {
      showError(password2, "Підтвердження пароля обов'язкове");
      return false;
    } else if (value !== passwordValue) {
      showError(password2, "Паролі не співпадають");
      return false;
    } else {
      showSuccess(password2);
      return true;
    }
  }

  // Перевірка згоди з умовами
  function validateTerms() {
    if (!terms.checked) {
      const formControl = terms.parentElement;
      let error = formControl.querySelector(".error-message");

      if (!error) {
        error = document.createElement("div");
        error.className = "error-message text-danger small mt-1";
        formControl.appendChild(error);
      }

      error.textContent = "Ви повинні погодитись з умовами";
      return false;
    } else {
      const formControl = terms.parentElement;
      const error = formControl.querySelector(".error-message");
      if (error) error.remove();
      return true;
    }
  }

  // Додаємо слухачів подій для валідації в реальному часі
  fullName.addEventListener("blur", validateFullName);
  email.addEventListener("blur", validateEmail);
  phone.addEventListener("blur", validatePhone);
  password.addEventListener("blur", validatePassword);

  // Перевіряємо збіг паролів при введенні
  password2.addEventListener("input", function () {
    if (password2.value.length > 0) {
      validatePassword2();
    }
  });

  password2.addEventListener("blur", validatePassword2);

  // Також перевіряємо збіг при зміні основного пароля
  password.addEventListener("input", function () {
    if (password2.value.length > 0) {
      validatePassword2();
    }
  });

  terms.addEventListener("change", validateTerms);

  // Валідація при відправці форми
  form.addEventListener("submit", function (e) {
    e.preventDefault();

    const isFullNameValid = validateFullName();
    const isEmailValid = validateEmail();
    const isPhoneValid = validatePhone();
    const isPasswordValid = validatePassword();
    const isPassword2Valid = validatePassword2();
    const isTermsValid = validateTerms();

    const isFormValid =
      isFullNameValid &&
      isEmailValid &&
      isPhoneValid &&
      isPasswordValid &&
      isPassword2Valid &&
      isTermsValid;

    if (isFormValid) {
      // Якщо всі поля валідні, відправляємо форму
      form.submit();
    } else {
      // Прокручуємо до першого поля з помилкою
      const firstError = form.querySelector(".is-invalid");
      if (firstError) {
        firstError.scrollIntoView({ behavior: "smooth", block: "center" });
        firstError.focus();
      }
    }
  });

  // Показуємо/ховаємо пароль
  function addPasswordToggle(input) {
    const wrapper = input.parentElement;
    wrapper.style.position = "relative";

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className =
      "btn btn-sm position-absolute end-0 top-50 translate-middle-y me-2";
    toggleBtn.style.border = "none";
    toggleBtn.style.background = "transparent";
    toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';

    toggleBtn.addEventListener("click", function () {
      if (input.type === "password") {
        input.type = "text";
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
      } else {
        input.type = "password";
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
      }
    });

    wrapper.appendChild(toggleBtn);
  }

  // Додаємо кнопки показу/приховування пароля
  addPasswordToggle(password);
  addPasswordToggle(password2);
});
