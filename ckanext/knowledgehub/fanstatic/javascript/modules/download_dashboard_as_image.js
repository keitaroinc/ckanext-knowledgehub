/*

This module downloads a dashboard as an image.

*/
ckan.module('download-dashboard-as-image', function ($) {
    return {
        initialize: function () {
            $('.site-footer').addClass('html2canvas-ignore')
            this.el.on('click', this._onClick.bind(this));
        },
        _onClick(event) {
            event.preventDefault();

            var nodeList = document.querySelectorAll('.c3-lines path');
            var nodeList2 = document.querySelectorAll('.c3-axis path');
            var line_graph = Array.from(nodeList);
            var x_and_y = Array.from(nodeList2);

            //fix weird back fill
            line_graph.forEach(function(element){
                element.style.fill = "none";
            });
            //fix axes
            x_and_y.forEach(function(element){
                element.style.fill = "none";
                element.style.stroke = "black";
            });
            // fix references
            d3.selectAll('.c3-ygrid-line.base line').attr("stroke", "grey");

            html2canvas(document.body, {
              //fix images
              ignoreElements: function(element) {
                if (element.classList.contains('html2canvas-ignore')) return true;
              },
            }).then(function(canvas) {
                Canvas2Image.saveAsPNG(canvas);
            });
        }
    }
});
