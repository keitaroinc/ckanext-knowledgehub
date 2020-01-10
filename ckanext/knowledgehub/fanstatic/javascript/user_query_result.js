(function (_, jQuery) {
    'use strict';

    const SKIP_PAGES = ['organization', 'group']
    const DATASET_TYPE = 'dataset'
    const RQ_TYPE = 'research_question'
    const DASHBOARD_TYPE = 'dashboard'
    const VISUALIZATION_TYPE = 'visualization'

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

    function saveUserQueryResult(result_type, result_id) {
        var url = window.location.href
        var parts = url.split('/')
        var page = parts[3]

        if (!SKIP_PAGES.includes(page)) {
            var query_text = $('#field-giant-search').val();
            if (query_text) {
                var user_id = $('#user-id').val();
                api.get('user_query_show', {
                    query_text: query_text,
                    user_id: user_id
                })
                .done(function (data) {
                    if (data.success) {
                        var query_id = data.result.id
                        api.post('user_query_result_create', {
                            query_id: query_id,
                            result_type: result_type,
                            result_id: result_id
                        })
                        .done(function (data) {
                            console.log("User Quere Result: SAVED!");
                        })
                        .fail(function (error) {
                            console.log("User Quere Result failed: " + error.statusText);
                        });
                    }
                })
                .fail(function (error) {
                    console.log("User Query Show failed: " + error.statusText);
                });
            }
        }
    }

    $(document).ready(function () {

        var save_user_query = function(callback) {
            var tab_content = $('.tab_content');

            tab_content.on('click', '.dataset-heading', function() {
                var dataset_content = $(this).parent('.dataset-content');
                var result_id = dataset_content.find('#dataset-id').val();
                callback(DATASET_TYPE, result_id);
            });

            tab_content.on('click', '.rq-heading', function () {
                var rq_content = $(this).parent('.rq-box');
                var result_id = rq_content.find('#rq-id').val();
                callback(RQ_TYPE, result_id);
            });

            tab_content.on('click', '.dashboard-link', function () {
                var dashboard_content = $(this).parent('#tabs-dashboards');
                var result_id = dashboard_content.find('#dashboard-id').val();
                callback(DASHBOARD_TYPE, result_id);
            });
        }

        save_user_query(function(result_type, result_id){
            // TODO: get user ID here
            saveUserQueryResult(result_type, result_id)
        });
    });
})(ckan.i18n.ngettext, $);