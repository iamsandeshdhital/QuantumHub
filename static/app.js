// Small progressive enhancements. The pages work without JavaScript; this
// only adds the "copy JSON" affordance on the lab output.

(function () {
  "use strict";

  function addCopyButton() {
    var result = document.getElementById("result");
    if (!result || result.dataset.copyReady === "true") {
      return;
    }
    result.dataset.copyReady = "true";

    var button = document.createElement("button");
    button.type = "button";
    button.className = "button button-small";
    button.textContent = "Copy JSON";
    button.addEventListener("click", function () {
      navigator.clipboard
        .writeText(result.textContent)
        .then(function () {
          button.textContent = "Copied";
          setTimeout(function () {
            button.textContent = "Copy JSON";
          }, 1500);
        })
        .catch(function () {
          button.textContent = "Copy failed";
        });
    });

    result.parentNode.insertBefore(button, result);
  }

  document.addEventListener("DOMContentLoaded", addCopyButton);
})();
