(function () {
  var map = window.GICLEE_HOME_SECTIONS;
  if (!map || typeof map !== 'object') return;

  function tagSection(hook, sectionKey) {
    if (!sectionKey) return;
    var el =
      document.getElementById('shopify-section-' + sectionKey) ||
      document.querySelector('.shopify-section[id*="' + sectionKey + '"]');
    if (el) el.setAttribute('data-giclee-home', hook);
  }

  Object.keys(map).forEach(function (hook) {
    tagSection(hook, map[hook]);
  });
})();
