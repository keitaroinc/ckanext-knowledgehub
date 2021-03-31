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

    var usefulBtn = $('#btn-useful');
    var unusefulBtn = $('#btn-unuseful');
    var trustedBtn = $('#btn-trusted');
    var untrustedBtn = $('#btn-untrusted');
    var userFeedbacks = {};
    var oppositeRF = {
        useful: 'unuseful',
        unuseful: 'useful',
        trusted: 'untrusted',
        untrusted: 'trusted'
    }


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
                if (data.success) {
                    var feedbacks = data.result;
                    feedbacks.forEach(function (feedback) {
                        var type = feedback.type;
                        userFeedbacks[type] = type;

                        var activeButton = $("#btn-" + type);
                        activeButton.attr('disabled', true);
                    });
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
                    var oppositeType = oppositeRF[type];
                    var newUserCount = $("#count-" + type);
                    var userCount = $("#count-" + oppositeType);

                    if (Object.keys(userFeedbacks).length > 0) {
                        if (userFeedbacks[oppositeType] !== undefined) {
                            removeDisabledAttr(oppositeType);
                            userCount.text(parseInt(userCount.text()) - 1);
                        }
                    }

                    newUserCount.text(parseInt(newUserCount.text()) + 1);
                    delete userFeedbacks[oppositeType];
                    userFeedbacks[type] = type;
                    btn.attr('disabled', true);
                }
            })
            .fail(function (error) {
                console.log("Add resource feedback: " + error.statusText);
            });
    };

    function removeDisabledAttr(type) {
        if (type === 'useful') {
            usefulBtn.removeAttr("disabled");
        } else if (type === 'unuseful') {
            unusefulBtn.removeAttr("disabled");
        } else if (type === 'trusted') {
            trustedBtn.removeAttr("disabled");
        } else if (type === 'untrusted') {
            untrustedBtn.removeAttr("disabled");
        }
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
