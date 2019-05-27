(function (_, jQuery) {
    'use strict';

    var timer = null;

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
        },
        post: function (action, data) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, data, 'json');
        }
    };

    $(document).ready(function () {
        $('#field-giant-search')
            .bind("change keyup", function (event) {
                clearTimeout(timer)
                if (event.keyCode !== 13) {
                    // detect that user has stopped typing for a while
                    timer = setTimeout(function() {
                        var text = $('#field-giant-search').val();
                        console.log('User input: ' + text)

                        if (text !== '') {
                            api.get('get_predictions', {
                                text: text
                            }, true)
                            .done(function (data) {
                                if (data.success) {
                                    var results = data.result;
                                    results.forEach(function (r) {
                                        console.log(text + r);
                                    });
                                }
                            })
                            .fail(function (error) {
                                console.log("Get predictions: " + error.statusText);
                            });
                        }
                    }, 500);
                }
            })
    });
})(ckan.i18n.ngettext, $);
