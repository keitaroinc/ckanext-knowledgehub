(function (_, jQuery) {
    'use strict';

    var api = {
        get: function (action, params, async) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            if (!async) {
                $.ajaxSetup({
                    async: false
                });
            }
            return $.getJSON(url);
        }
    };

    function populateSubThemes() {
        var theme = $('#theme').val();
        var sub_theme = $('#sub_theme').val();
        console.log(sub_theme)
        api.get('sub_theme_list', {
            'theme': theme
        })
        .done(function (data) {
            $('#sub_theme').empty();
            for (var i = 0; i < data.result.data.length; ++i) {
                $('#sub_theme').append(new Option(data.result.data[i].title, data.result.data[i].id));
            }
        });
    }

    $(document).ready(function () {
        $('#theme').change(function () {
            console.log('OK')
            populateSubThemes();
        })
    });
})(ckan.i18n.ngettext, $);

