function enableTooltips() {
    $(".item").each(function() {
        var e = $(this)
          , t = $(this).attr("id")
          , a = $("#" + t + "_tooltip");
        e.on("mousemove", function (e) {
            if (window.outerWidth > 600){
                var x = (e.clientX + 20),
                    y = (e.clientY + window.scrollY + 20);
                    x = x + a.width() < window.innerWidth? x : e.clientX - a.width()
                    y = y + a.height() < window.innerHeight? y : e.clientY + window.scrollY - a.height() - 20
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
};