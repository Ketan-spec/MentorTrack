// Wait for the DOM to load
document.addEventListener("DOMContentLoaded", () => {
  console.log("MentorTrack: index page loaded ✅");

  // Smooth scroll for internal links (like Explore Features)
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) target.scrollIntoView({ behavior: "smooth" });
    });
  });

  // Highlight active nav link
  const currentPage = window.location.pathname.split("/").pop();
  document.querySelectorAll(".navbar-link").forEach(link => {
    if (link.getAttribute("href") === currentPage) {
      link.classList.add("active-link");
    }
  });

  // Handle "Get Started" button behavior (optional)
  const ctaButton = document.querySelector("#i3quw");
  if (ctaButton) {
    ctaButton.addEventListener("click", () => {
      window.location.href = "signup.html";
    });
  }
});
