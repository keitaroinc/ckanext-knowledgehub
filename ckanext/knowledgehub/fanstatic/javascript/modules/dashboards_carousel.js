/*

This module initializes a carousel for dashboards.

*/
ckan.module('dashboards_carousel', function ($) {
    return {
        initialize: function () {
            this.el.removeClass('hidden');
            $('.dashboard-carousel').slick({
                dots: true
            });
        }
    }
});
