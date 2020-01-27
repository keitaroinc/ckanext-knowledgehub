(function (_, jQuery) {
    'use strict';

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

    function removeIntent(tr) {
        var intentID = tr.get(0).cells[0].innerHTML;

        api.get('user_intent_delete', {
            id: intentID
        })
        .done(function(data) {
            if (data.success) {
                tr.detach();
            }
        })
        .fail(function(error) {
            console.log("User intent delete: " + error.statusText);
        });
    };

    $(document).ready(function () {
        var $table = $('#intents');
        $table.DataTable({
            "paging": true,
            "iDisplayLength": 25
        });

        $('.dataTables_length').addClass('bs-select');
        $table.removeClass('dataTable');

        var modalConfirm = function(callback) {
            var tr;
            var modalDelete = $('#modalDelete');

            $table.on('click', '.table-remove', function() {
                tr = $(this).parents('tr');
                modalDelete.modal('show');
            });

            $('#btnYes').on('click', function(){
                callback(true, tr);
                modalDelete.modal('hide');
            });

            $('#btnNo').on('click', function() {
                callback(false, tr);
                modalDelete.modal('hide');
            })

        }

        modalConfirm(function(confirm, tr) {
            if(confirm) {
                removeIntent(tr);
            }
        });
    });
})(ckan.i18n.ngettext, $);