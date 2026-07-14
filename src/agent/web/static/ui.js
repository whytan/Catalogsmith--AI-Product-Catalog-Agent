(() => {
  document.querySelectorAll("[data-workspace]").forEach((layout) => {
    const toggle = layout.querySelector(".workspace-toggle");
    if (!toggle) return;
    toggle.addEventListener("click", () => {
      const open = layout.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  const shopToolbar = document.querySelector(".shop-toolbar-sticky");
  if (shopToolbar) {
    const observer = new IntersectionObserver(
      ([entry]) => shopToolbar.classList.toggle("is-stuck", !entry.isIntersecting),
      { threshold: 1, rootMargin: "-70px 0px 0px 0px" },
    );
    const sentinel = document.createElement("div");
    sentinel.style.height = "1px";
    shopToolbar.parentNode?.insertBefore(sentinel, shopToolbar);
    observer.observe(sentinel);
  }
})();
