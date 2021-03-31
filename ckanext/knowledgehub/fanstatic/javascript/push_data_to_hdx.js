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
                document.getElementById("hdx-loader").style.visibility = "hidden";
            });
    };

    function removeResourceHDX(tr) {
        document.getElementById("hdx-loader").style.visibility = "visible";
        var id = $('#package-name').val();
        var res_id = $('#resource-id').val();
        var res_name = $('#resource-name').val();
        var btn = $(this);
        var flash_messages = $('.flash-messages');
        btn.attr('disabled', true);
        api.post('delete_resource_from_hdx', {
            id: id,
            resource_name: res_name, 
            resource_id : res_id
        })
            .done(function (data) {
                if (data.success) {
                    btn.attr('disabled', false);
                    flash_messages.empty();
                    flash_messages.append('<div class="alert alert-warning fade in alert-info" data-ol-has-click-handler>Successfully deleted resource from HDX! <a class="close" href="#">x</a></div>');
                }
                document.getElementById("hdx-loader").style.visibility = "hidden";
            })
            .fail(function (error) {
                btn.attr('disabled', false);
                flash_messages.empty();
                flash_messages.append('<div class="alert alert-danger fade in alert-info" data-ol-has-click-handler>Delete resource from HDX: ' + error.statusText + '<a class="close" href="#">x</a></div>');
                document.getElementById("hdx-loader").style.visibility = "hidden";
            });
    };

    function addResourceHDX(tr) {
        document.getElementById("hdx-loader").style.visibility = "visible";
        var id = $('#package-name').val();
        var res_id = $('#resource-id').val();
        var res_name = $('#resource-name').val();
        var btn = $(this);
        var flash_messages = $('.flash-messages');
        btn.attr('disabled', true);
        api.post('upsert_resource_to_hdx', {
            dataset_name: id,
            resource_name: res_name, 
            resource_id : res_id
        })
            .done(function (data) {
                if (data.success) {
                    btn.attr('disabled', false);
                    flash_messages.empty();
                    flash_messages.append('<div class="alert alert-warning fade in alert-info" data-ol-has-click-handler>Successfully added resource to HDX! <a class="close" href="#">x</a></div>');
                }
                document.getElementById("hdx-loader").style.visibility = "hidden";
            })
            .fail(function (error) {
                btn.attr('disabled', false);
                flash_messages.empty();
                flash_messages.append('<div class="alert alert-danger fade in alert-info" data-ol-has-click-handler>Add resource to HDX: ' + error.statusText + '<a class="close" href="#">x</a></div>');
                document.getElementById("hdx-loader").style.visibility = "hidden";
            });
    };

    function removeDatasetHDX(tr) {
        document.getElementById("hdx-loader").style.visibility = "visible";
        var id = $('#package-name').val();
        var btn = $(this);
        var flash_messages = $('.flash-messages');
        btn.attr('disabled', true);
        api.post('delete_package_from_hdx', {
            id: id,
        })
            .done(function (data) {
                if (data.success) {
                    btn.attr('disabled', false);
                    flash_messages.empty();
                    flash_messages.append('<div class="alert alert-warning fade in alert-info" data-ol-has-click-handler>Successfully deleted dataset from HDX! <a class="close" href="#">x</a></div>');
                    
                }
                document.getElementById("hdx-loader").style.visibility = "hidden";
            })
            .fail(function (error) {
                btn.attr('disabled', false);
                flash_messages.empty();
                flash_messages.append('<div class="alert alert-danger fade in alert-info" data-ol-has-click-handler>Delete dataset from HDX: ' + error.statusText + '<a class="close" href="#">x</a></div>');
                document.getElementById("hdx-loader").style.visibility = "hidden";
            });
    };


    $(document).ready(function () {
        var package_id = $('#package-name').val();
        var pushBtn = $('#pushHDX');
        pushBtn.click(pushDataHDX.bind(pushBtn, package_id));

        var removeDatasetHDXBtn = $('#removeHDX')
        removeDatasetHDXBtn.click(removeDatasetHDX.bind(removeDatasetHDXBtn, package_id))
        
        var resource_name = $('resource-name').val();
        var value_name = document.getElementById('pushResourceHDX').value;
        var pushResource = $('#pushResourceHDX');
        if(value_name == "")
            pushResource.click(addResourceHDX.bind(pushResource, resource_name));      
        else
            pushResource.click(removeResourceHDX.bind(pushResource, resource_name));
    });



})(ckan.i18n.ngettext, $);

