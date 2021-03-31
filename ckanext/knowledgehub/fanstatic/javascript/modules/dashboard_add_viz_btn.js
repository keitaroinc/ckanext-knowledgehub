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

/*

This module handles adding new viz form.

*/
ckan.module('knowledgehub-dashboard-add-viz-btn', function ($) {
    return {
        initialize: function () {
            this.el.on('click', this._onClick.bind(this));
            var total_viz = $('.internal-dashboard-viz-container-item').length;
            this.state = {
                total_viz: total_viz
            };
            this.sandbox.subscribe('knowledgehub:remove-viz', function() {
                this.state.total_viz = --this.state.total_viz;
            }.bind(this));
        },
        _onClick(event) {
            event.preventDefault();

            this.state.total_viz = ++this.state.total_viz;

            var module_options = {
                position: this.state.total_viz
            }

            this.sandbox.client.getTemplate('internal_dashboard_visualization.html',
                module_options,
                this._onReceiveSnippet.bind(this)
            );
        },
        _onReceiveSnippet(html) {
            $('.internal-dashboard-viz-container-items').append(html)

            var select = $('select[name=research_question_' + this.state.total_viz + ']');

            window.research_questions.forEach(function(rq) {
                select.append('<option value="' + rq.value + '">' + rq.text + '</option>')
            });

            var removeBtn = $('div[data-viz-position=' + this.state.total_viz + ']').find('.remove-viz-btn-internal-dashboard');

            window.ckan.module.initializeElement(select[0]);
            window.ckan.module.initializeElement(removeBtn[0]);
        }
    }
});
