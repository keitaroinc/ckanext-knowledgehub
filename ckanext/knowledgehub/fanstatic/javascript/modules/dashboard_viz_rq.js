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

This module handles listing visualizations based on a research question.

*/
ckan.module('knowledgehub-dashboard-viz-rq', function ($) {
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
            this.el.on('change', this.selectRQ.bind(this));
            this.vizContainerItem = $('div[data-viz-position=' + this.options.position + ']').find('.internal-dashboard-viz-container-item-view');
            this.vizDropdown = $('div[data-viz-position=' + this.options.position + ']').find('.internal-dashboard-viz-dropdown')
            this.vizDropdownSelect = this.vizDropdown.find('select');
            this.sizeDropdown = $('div[data-viz-position=' + this.options.position + ']').find('.internal-dashboard-size-dropdown');

            if (this.options.position !== 1) {
                window.ckan.module.initializeElement(this.vizDropdownSelect[0]);
            }

        },
        selectRQ() {
            this.vizContainerItem.html('');
            this.vizDropdownSelect.html('');

            if (!this.el.val()) {
                this.vizDropdown.css({ display: 'none' });
                this.sizeDropdown.css({ display: 'none' });
                return;
            }

            var RQValue = $('option[value=' + this.el.val() + ']').val()

            if (RQValue) {
                api.get('visualizations_for_rq', { research_question: RQValue})
                    .done(function(data) {
                        if (data.success) {
                            this.vizDropdown.css({ display: 'block' });
                            if (data.result.length > 0) {
                                this.vizDropdownSelect.append('<option value="" selected>Choose visualization</option>')
                                data.result.forEach(function(resView) {
                                    this.vizDropdownSelect.append('<option value="' + resView.id + '" data-resource-view="' + window.encodeURIComponent(JSON.stringify(resView)) + '">' + resView.title + '</option>');
                                }.bind(this))
                            } else {
                                this.vizDropdownSelect.append('<option value="" selected>No visualizations found</option>')
                            }
                        } else {
                            alert(this._('Could not get visualizations for research question: ' + RQValue));
                        }
                    }.bind(this))
            } else {
                this.vizDropdown.css({ display: 'none' });
            }
        }
    }
});

