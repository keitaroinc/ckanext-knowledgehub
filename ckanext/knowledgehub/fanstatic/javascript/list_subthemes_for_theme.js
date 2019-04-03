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
        api.get('sub_theme_list', {
            'theme': theme
        }, true)
        .done(function (data) {
            $('#sub_theme').empty();
            if(data.result.data.length != 0)
            {
                $('#sub_theme').append(new Option("Select sub-theme"), '');
                if(theme !="")
                    for (var i = 0; i < data.result.data.length; ++i) {
                        $('#sub_theme').append(new Option(data.result.data[i].title, data.result.data[i].id));
                    }
                else
                {
                    $('#sub_theme').empty();
                    $('#sub_theme').append(new Option("Please select a theme first!"));  
                } 
            }
            else {
                $('#sub_theme').append(new Option("This theme does not have any sub-themes"));
            }
        });
    }

    $(document).ready(function () {
        $("#sub_theme").append(new Option("Please select a theme first!"));
        $('#theme').change(function () {
            populateSubThemes();
        })
    });
})(ckan.i18n.ngettext, $);

