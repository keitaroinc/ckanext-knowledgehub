/*
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

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
        if(theme) {
            api.get('sub_theme_list', {
                'theme': theme
            }, true)
            .done(function (data) {
                $('#sub_theme').empty();
                $('#sub_theme').append(new Option("Select sub-theme", ""));
                for (var i = 0; i < data.result.data.length; ++i) {
                    $('#sub_theme').append(new Option(data.result.data[i].title, data.result.data[i].id));
                }
            });
        } else {
            $('#sub_theme').empty();
            $('#sub_theme').append(new Option("Select sub-theme", ""));
        }


    }

    $(document).ready(function () {
        $('#theme').change(function () {
            populateSubThemes();
        })
    });
})(ckan.i18n.ngettext, $);

