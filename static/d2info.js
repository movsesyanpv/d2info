function enableTooltips() {
    $(".item").each(function() {
        var e = $(this)
          , t = $(this).attr("id")
          , a = $("#" + t + "_tooltip");
        e.on("mousemove", function (e) {
            var x = (e.clientX + 20),
                y = (e.clientY + window.scrollY + 20);
            for (var i = 0; i < a.length; i++) {
                x = x + a.width() < window.innerWidth? x : e.clientX - a.width()
                y = y + a.height() < window.innerHeight? y : e.clientY + window.scrollY - a.height() - 20
                a.attr("style", "left: " + x + "px; top: " + y + "px;")
            }
        })
    })
}
$(document).on("afterEventsParsed", function() {
    enableTooltips()
});