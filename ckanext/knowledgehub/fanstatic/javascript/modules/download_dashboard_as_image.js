/*
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

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

