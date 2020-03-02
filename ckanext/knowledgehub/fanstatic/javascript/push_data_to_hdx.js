// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

(function (_, jQuery) {
    'use strict';

    var api = {
        post: function (action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            return $.post(url, params, 'json');
        }
    };

    function pushDataHDX(tr) {
        var id = $('#package-name').val();
        var btn = $(this);
        api.post('push_dataset_to_hdx', {
            id: id
        })
            .done(function (data) {
                if (data.success) {
                    btn.attr('disabled', true);
                }
            })
            .fail(function (error) {
                console.log("Push data to HDX: " + error.statusText);
            });
    };

    $(document).ready(function () {
        var package_id = $('#package-name').val();
        var pushBtn = $('#pushHDX');

        pushBtn.click(pushDataHDX.bind(pushBtn, package_id));
    });



})(ckan.i18n.ngettext, $);

