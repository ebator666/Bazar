document.addEventListener("DOMContentLoaded", () => {
  const logoContainer = document.getElementById("logoContainer");
  const subtitle = document.getElementById("subtitle");
  const letters = ["B", "A", "Z", "A", "R"];

  let animationId;
  let startTime;
  let isVisible = false;

  // Создание отдельные буквы BAZAR
  function initLetters() {
    logoContainer.innerHTML = "";
    letters.forEach((letter) => {
      const span = document.createElement("span");
      span.textContent = letter;
      span.className = "logo-letter";
      logoContainer.appendChild(span);
    });
  }

  // Появление букв
  function showLetters() {
    const letterElements = document.querySelectorAll(".logo-letter");
    letterElements.forEach((el, i) => {
      setTimeout(() => el.classList.add("visible"), i * 150);
    });
    setTimeout(() => subtitle.classList.add("visible"), 1200);
  }

  // Волновой полёт ( для 5 букв)
  function animate(currentTime = performance.now()) {
    if (!isVisible) return;

    const elapsed = currentTime - startTime;
    const letterElements = document.querySelectorAll(".logo-letter");

    letters.forEach((_, i) => {
      if (letterElements[i]) {
        const xWave = Math.sin(elapsed * 0.0012 + i * 0.9) * (0.8 + i * 0.3);
        const yWave = Math.sin(elapsed * 0.0018 + i * 1.4) * (1.2 + i * 0.3);
        const scale = 1 + Math.sin(elapsed * 0.002 + i) * 0.05; //  дыхание
        letterElements[i].style.transform =
          `scale(${scale}) translate(${xWave}px, ${yWave}px)`;
      }
    });

    animationId = requestAnimationFrame(animate);
  }

  // Запуск
  initLetters();

  setTimeout(() => {
    isVisible = true;
    showLetters();
    startTime = performance.now();
    animate();
  }, 800);

  // Очистка
  window.addEventListener("beforeunload", () => {
    if (animationId) cancelAnimationFrame(animationId);
  });
});

// Кнопка возврата (без изменений)
const backButton = document.getElementById("backButton");

function initMenu() {
  // Анимация кнопки возврата
  setTimeout(() => {
    backButton.style.opacity = "1";
    backButton.style.transform = "translateY(0)";
  }, 400);
}

setTimeout(() => {
  const subtitleLink = document.getElementById("subtitleLink");
  if (subtitleLink) subtitleLink.classList.add("visible");
}, 1200);
