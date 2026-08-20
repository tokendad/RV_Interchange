const activeNav = document.body.dataset.activeNav || undefined;
const headerSlot = document.getElementById("header-slot");
const footerSlot = document.getElementById("footer-slot");

if (headerSlot) {
  headerSlot.replaceWith(renderHeader(activeNav));
}
if (footerSlot) {
  footerSlot.replaceWith(renderFooter());
}
