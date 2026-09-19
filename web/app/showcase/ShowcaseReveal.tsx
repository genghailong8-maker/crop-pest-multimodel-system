"use client";

import { useEffect } from "react";

export default function ShowcaseReveal() {
  useEffect(() => {
    const root = document.documentElement;
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-showcase-reveal]"));

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      elements.forEach((element) => element.dataset.showcaseVisible = "true");
      return;
    }

    root.classList.add("showcase-motion-ready");
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        (entry.target as HTMLElement).dataset.showcaseVisible = "true";
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -10%", threshold: 0.12 });

    elements.forEach((element) => observer.observe(element));
    return () => {
      observer.disconnect();
      root.classList.remove("showcase-motion-ready");
    };
  }, []);

  return null;
}
