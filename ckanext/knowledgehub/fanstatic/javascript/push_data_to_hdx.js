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
        document.getElementById("hdx-loader").style.visibility = "visible";
        var id = $('#package-name').val();
        var btn = $(this);
        var flash_messages = $('.flash-messages');
        btn.attr('disabled', true);
        api.post('upsert_dataset_to_hdx', {
            id: id
        })
            .done(function (data) {
                if (data.success) {
                    btn.attr('disabled', false);
                    flash_messages.empty();
                    flash_messages.append('<div class="alert alert-warning fade in alert-info" data-ol-has-click-handler>Successfully pushed data to HDX! <a class="close" href="#">x</a></div>');
                }
                document.getElementById("hdx-loader").style.visibility = "hidden";
            })
            .fail(function (error) {
                btn.attr('disabled', false);
                flash_messages.empty();
                flash_messages.append('<div class="alert alert-danger fade in alert-info" data-ol-has-click-handler>Push data to HDX: ' + error.statusText + '<a class="close" href="#">x</a></div>');
            });
    };

    $(document).ready(function () {
        var package_id = $('#package-name').val();
        var pushBtn = $('#pushHDX');

        pushBtn.click(pushDataHDX.bind(pushBtn, package_id));
    });



})(ckan.i18n.ngettext, $);

