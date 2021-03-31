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

// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

function showValidationForm() {
    document.getElementById('validationForm').style.display = "block";

}

function hideValidationForm() {
    document.getElementById('validationForm').style.display = "display:none";
}

function editComment() {
    document.getElementById('editComment').style.display = "block";

}

(function (_, jQuery) {
    'use strict';

    var api = {
        post: function (action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            return $.post(url, params, 'json');
        },
        delete: function (action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, params, 'json');
        },
        update: function (action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, params, 'json');
        }
    };

    function resourceValidationReport() {
        var resource = $('#resource').val();
        var validationWhat = $('#comment').val();
        var btn = $(this);
        api.post('resource_validate_create', {
            what: validationWhat,
            resource: resource
        })
            .done(function (data) {
                if (data.success) {
                    btn.attr('disabled', true);
                }
            })
            .fail(function (error) {
                console.log("Add validation report: " + error.statusText);
            });
    };

    function resourceValidationDelete(tr) {
        var resource = $('#resource').val();
        api.delete('resource_validate_delete', {
            id: resource
        })
            .done(function () {
                console.log("Validation Report: DELETED!");
            })
            .fail(function (error) {
                console.log("Delete validation report: " + error.statusText);
            });
    };

    function resourceValidationEdit() {
        var resource = $('#resource').val();
        var validationWhat = $('#commentInput').val();
        var btn = $(this);
        api.update('resource_validate_update', {
            id: resource,
            what: validationWhat
        })
            .done(function () {
                console.log("Validation Report: UPDATED!");
            })
            .fail(function (error) {
                console.log("Edit validation report: " + error.statusText);
            });
    };

    $(document).ready(function () {
        var resource = $('#resource').val();
        var validationWhat = $('#comment').val();
        var validationDescription = $('#commentInput').val();
        var validationBtn = $('#validationSubmitSuccess');
        var deleteBtn = $('#delete_validation')
        var editBtn = $('#validationEdited')
        validationBtn.click(resourceValidationReport.bind(validationBtn, validationWhat, resource));
        deleteBtn.click(resourceValidationDelete.bind(deleteBtn, resource));
        editBtn.click(resourceValidationEdit.bind(editBtn, resource, validationDescription));
    });



})(ckan.i18n.ngettext, $);