(function (_, jQuery) {
    'use strict';

    var usefulBtn = $('#btn-useful');
    var unusefulBtn = $('#btn-unuseful');
    var trustedBtn = $('#btn-trusted');
    var untrustedBtn = $('#btn-untrusted');
    var userFeedback = '';

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

    function setActiveFeedback(resource) {
        api.get('resource_user_feedback', {
            resource: resource
        })
        .done(function (data) {
            console.log(data)
            if (data.success) {
                var feedback =  data.result;
                var type = feedback.type;
                userFeedback = type;

                var activeButton = $("#btn-" + type);
                activeButton.attr('disabled', true);
            }
        })
        .fail(function (error) {
            console.log("Resource feedback: " + error.statusText);
        });
    };

    function resourceFeedback(type, resource, dataset) {
        var btn = $(this);
        api.post('resource_feedback', {
            type: type,
            resource: resource,
            dataset: dataset
        })
        .done(function (data) {
            if (data.success) {
                var userCount = $("#count-" + userFeedback);
                var newUserCount = $("#count-" + type);
                if (userFeedback) {
                    removeDisabledAttr();

                    userCount.text(parseInt(userCount.text()) - 1);
                    newUserCount.text(parseInt(newUserCount.text()) + 1);
                } else {
                    newUserCount.text(parseInt(newUserCount.text()) + 1);
                }

                userFeedback = type;
                btn.attr('disabled', true);
            }
        })
        .fail(function (error) {
            console.log("Add resource feedback: " + error.statusText);
        });
    };

    function removeDisabledAttr() {
        usefulBtn.removeAttr("disabled");
        unusefulBtn.removeAttr("disabled");
        trustedBtn.removeAttr("disabled");
        untrustedBtn.removeAttr("disabled")
    };

    $(document).ready(function () {
        var resource = $('#resource').val();
        var dataset = $('#dataset').val();
        setActiveFeedback(resource);

        usefulBtn.click(resourceFeedback.bind(usefulBtn, 'useful', resource, dataset));
        unusefulBtn.click(resourceFeedback.bind(unusefulBtn, 'unuseful', resource, dataset));
        trustedBtn.click(resourceFeedback.bind(trustedBtn, 'trusted', resource, dataset));
        untrustedBtn.click(resourceFeedback.bind(untrustedBtn, 'untrusted', resource, dataset));
    });
})(ckan.i18n.ngettext, $);
