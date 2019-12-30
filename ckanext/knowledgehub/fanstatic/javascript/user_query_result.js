(function (_, jQuery) {
    'use strict';

    const SKIP_PAGES = ['organization', 'group']

    var api = {
        get: function (action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            return $.getJSON(url);
        },
        post: function (action, data) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, data, 'json');
        }
    };

    $(document).ready(function () {
        $('.dataset-list').on('click', '.dataset-heading', function() {
            var url = window.location.href
            var parts = url.split('/')
            var page = parts[3]

            // only perform this action on home page
            if (! SKIP_PAGES.includes(page)) {
            }
        });
    });
})(ckan.i18n.ngettext, $);