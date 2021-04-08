/*
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

/*

This module handles displaying a visualization from a dropdown of resource views.

*/
ckan.module('knowledgehub-dashboard-viz-select', function ($) {
    var api = {
        get: function(action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            return $.getJSON(url);
        },
        post: function(action, data) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, data, 'json');
        }
    };

    return {
        initialize: function () {
            this.el.on('change', this._selectViz.bind(this));
            this.vizContainerItem = $('div[data-viz-position=' + this.options.position + ']').find('.internal-dashboard-viz-container-item-view');
            this.sizeDropdown = $('div[data-viz-position=' + this.options.position + ']').find('.internal-dashboard-size-dropdown');
            $.each(this.el.find('option'), function(i, el) {
                el = $(el);
                res_view_id = el.attr('value');
                if (res_view_id) {
                    api.get('resource_view_show', { id: res_view_id })
                        .done(function(data) {
                            el.attr('data-resource-view', window.encodeURIComponent(JSON.stringify(data.result)))
                        })
                }
            })
        },
        _selectViz() {
            this.vizContainerItem.html('')

            if (!this.el.val()) {
                this.sizeDropdown.css({display: 'none'})
                return;
            }

            var currentOption = this.el.find('option[value=' + this.el.val() + ']')
            var resView = currentOption.attr('data-resource-view')

            if (resView) {
                this.sizeDropdown.css({ display: 'block' })
                var position = this.el.attr('data-module-position')
                var snippetName;
                resView = JSON.parse(window.decodeURIComponent(resView))

                if (resView.view_type === 'chart') {
                    snippetName = 'chart_module.html'
                    resView.__extras.colors = resView.__extras.color;
                    resView.__extras.chart_type = resView.__extras.type;
                    resView.__extras.data_sort = resView.__extras.sort;
                } else if (resView.view_type === 'table') {
                    snippetName = 'table_module.html'
                    resView.__extras.table_title = resView.__extras.title;
                    resView.__extras.resource_id = resView.id;
                } else if (resView.view_type === 'map') {
                    snippetName = 'map_module.html'
                    var map_config = $('div[data-map-config]').attr('data-map-config')
                    resView.__extras.map_config = map_config
                }

                this.sandbox.client.getTemplate(snippetName,
                    resView.__extras,
                    this._onReceiveSnippet.bind(this)
                );
            }
        },
        _onReceiveSnippet(html) {
            this.vizContainerItem.append(html)
            var resViewModule = this.vizContainerItem.find('div[data-module]')
            window.ckan.module.initializeElement(resViewModule[0]);
        }
    }
});

