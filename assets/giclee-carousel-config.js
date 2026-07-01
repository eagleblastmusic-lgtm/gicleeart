/** Domyślne ustawienia sekcji «Wybrane dzieła» (GicleeApp → Karuzela). */
window.__GICLEE_CAROUSEL_DEFAULT = "Karuzela2";
window.__GICLEE_SHOWCASE_LOOK_DEFAULT = "V2";
(function (d) {
  try {
    var look = window.__GICLEE_SHOWCASE_LOOK_DEFAULT;
    if (look === "V1" || look === "V2" || look === "V3") {
      d.documentElement.setAttribute("data-giclee-showcase-look", look);
    }
  } catch (_e) {}
})(document);
