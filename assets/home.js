(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // --- Nav theme ---
  const nav = $(".nav");
  const hero = $(".hero-frame");
  function updateNav() {
    const y = window.scrollY;
    const heroBottom = hero.getBoundingClientRect().bottom + y - 80;
    nav.classList.toggle("on-dark", y < heroBottom);
  }
  window.addEventListener("scroll", updateNav, { passive: true });
  window.addEventListener("resize", updateNav);
  updateNav();

  // --- Reveal on scroll ---
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
  $$(".reveal").forEach(el => io.observe(el));

  // --- FAQ ---
  $$(".faq-item").forEach((item) => {
    item.addEventListener("click", () => {
      const wasOpen = item.classList.contains("open");
      $$(".faq-item").forEach(i => i.classList.remove("open"));
      if (!wasOpen) item.classList.add("open");
    });
  });

  // --- Orbit gallery ---
  const stage = $(".orbit-stage");
  if (stage) {
    const track = $(".orbit-track", stage);
    const items = $$(".orbit-item", track);
    const caption = $(".orbit-caption");
    const N = items.length;
    let angle = 0;
    let target = 0;
    let dragging = false;
    let startX = 0, startA = 0;
    let auto = true;

    items.forEach((el, i) => { el.dataset.baseAngle = (360 / N) * i; });

    function render() {
      const r = Math.min(520, Math.max(260, window.innerWidth * 0.3));
      items.forEach((el) => {
        const a = (+el.dataset.baseAngle + angle) * Math.PI / 180;
        const x = Math.sin(a) * r;
        const z = Math.cos(a) * r;
        const rotY = -((+el.dataset.baseAngle + angle));
        el.style.transform = `translate3d(${x}px, 0, ${z}px) rotateY(${rotY}deg)`;
        el.style.zIndex = Math.round(z + 1000);
        el.style.opacity = Math.max(0.25, (z + r) / (2 * r)).toFixed(2);
      });
      let best = 0, bestZ = -Infinity;
      items.forEach((el, i) => {
        const a = (+el.dataset.baseAngle + angle) * Math.PI / 180;
        const z = Math.cos(a);
        if (z > bestZ) { bestZ = z; best = i; }
      });
      if (caption) {
        const active = items[best];
        const title = active.dataset.title || "";
        const n = String(best + 1).padStart(2, "0") + " / " + String(N).padStart(2, "0");
        caption.innerHTML = `“${title}”<span class="num">${n}</span>`;
      }
    }

    function tick() {
      if (!dragging && auto) target -= 0.18;
      angle += (target - angle) * 0.08;
      render();
      requestAnimationFrame(tick);
    }

    stage.addEventListener("pointerdown", e => {
      dragging = true; auto = false;
      startX = e.clientX; startA = target;
      stage.setPointerCapture(e.pointerId);
    });
    stage.addEventListener("pointermove", e => {
      if (!dragging) return;
      target = startA + (e.clientX - startX) * 0.3;
    });
    const stop = () => { dragging = false; };
    stage.addEventListener("pointerup", stop);
    stage.addEventListener("pointercancel", stop);

    $("#orbit-prev")?.addEventListener("click", () => { auto = false; target += 360 / N; });
    $("#orbit-next")?.addEventListener("click", () => { auto = false; target -= 360 / N; });
    $("#orbit-play")?.addEventListener("click", (e) => {
      auto = !auto;
      e.currentTarget.textContent = auto ? "❚❚" : "▶";
    });

    render();
    tick();
    window.addEventListener("resize", render);
  }

  // --- Phone prototype animation ---
  const sheet = $("#phoneSheet");
  const pins = [$("#phonePin1"), $("#phonePin2"), $("#phonePin3")].filter(Boolean);
  // Grab the live blob URL the bundler already assigned to the sheet image;
  // re-assigning raw UUIDs here would produce 404s and fire bundle errors.
  const initialSheetImgEl = document.getElementById("sheetImg");
  const initialSheetImg = initialSheetImgEl ? initialSheetImgEl.src : "";
  const stories = [
    {
      k: "№ 001 · Хрещатик",
      t: "Маєток Онуфрія Головинського",
      a: "1797 · ранній класицизм / ампір",
      img: initialSheetImg,
      txt: "Одна з перших знакових споруд на Хрещатику і фактичний початок забудови майбутньої головної вулиці Києва. У той час Хрещатик ще не був міським бульваром — це була напівпорожня долина між історичними частинами міста. Головинський звів тут двоповерховий палацовий будинок у стилі раннього класицизму / ампіру.",
      chips: ["Класицизм", "Ампір", "1797"]
    }
  ];

  let curPin = 0;
  function setStory(i) {
    const s = stories[i];
    if (!s) return;
    const kEl = $("#sheetK"); if (kEl) kEl.textContent = s.k;
    const tEl = $("#sheetT"); if (tEl) tEl.textContent = s.t;
    const aEl = $("#sheetA"); if (aEl) aEl.textContent = s.a;
    const imgEl = $("#sheetImg"); if (imgEl && s.img) imgEl.src = s.img;
    const txtEl = $("#sheetTxt"); if (txtEl) txtEl.textContent = s.txt;
    const chipsEl = $("#phoneSheet .chips");
    if (chipsEl) chipsEl.innerHTML = s.chips.map(c => `<span>${c}</span>`).join("");
    pins.forEach((p, idx) => {
      if (p) p.classList.toggle("pulse", idx === i);
    });
  }

  pins.forEach((p, i) => {
    p.addEventListener("click", () => {
      curPin = i;
      setStory(i);
      if (sheet && sheet.classList.contains("collapsed")) sheet.classList.remove("collapsed");
    });
  });

  // Auto-cycle through pins when phone is in view
  if (sheet) {
    const phoneIO = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) startCycle();
        else stopCycle();
      });
    }, { threshold: 0.3 });
    phoneIO.observe(sheet);

    let cycleTimer = null;
    function startCycle() {
      // Single story — no cycling needed
      stopCycle();
      if (stories.length > 1) {
        cycleTimer = setInterval(() => {
          curPin = (curPin + 1) % stories.length;
          sheet.classList.add("collapsed");
          setTimeout(() => {
            setStory(curPin);
            sheet.classList.remove("collapsed");
          }, 500);
        }, 4200);
      }
    }
    function stopCycle() {
      if (cycleTimer) { clearInterval(cycleTimer); cycleTimer = null; }
    }

    sheet.addEventListener("click", () => {
      sheet.classList.toggle("collapsed");
    });
  }

  // --- Waitlist form ---
  const form = $(".waitlist form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const btn = form.querySelector("button");
      btn.textContent = "Вас додано ✓";
      form.querySelector("input").value = "";
      setTimeout(() => { btn.textContent = "Приєднатися"; }, 2800);
    });
  }
})();
