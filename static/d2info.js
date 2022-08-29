function enableTooltips() {
    $(".item").each(function() {
        var e = $(this)
          , t = $(this).attr("id")
          , a = $("#" + t + "_tooltip");
        e.on("mousemove", function (e) {
            if (window.outerWidth > 600){
                var x = (e.clientX + 20),
                    y = (e.clientY + window.scrollY + 20);
                    x = this.offsetLeft + this.offsetWidth + a.outerWidth() < window.innerWidth ? x : e.clientX - a.outerWidth()
                    y = this.offsetTop + this.offsetHeight + a.outerHeight() - window.scrollY < window.innerHeight ? y : e.clientY + window.scrollY - a.outerHeight() - 20
            }
            else{
                var x = 0,
                    y = window.outerHeight/2 + window.scrollY;
            }
            for (var i = 0; i < a.length; i++) {
                    a.attr("style", "left: " + x + "px; top: " + y + "px;")
                }
        })
    })
}
window.onload = function() {
    enableTooltips()
    var hiddenElement = document.getElementById("main_point");
    hiddenElement.scrollIntoView({block: "center", behavior: "smooth"});
};
function header() {
  var x = document.getElementById("myTopnav");
  if (x.className === "topnav") {
    x.className += " responsive";
  } else {
    x.className = "topnav";
  }
}