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

This module handles removing a viz form.

*/
ckan.module('knowledgehub-dashboard-remove-viz-btn', function ($) {
    return {
        initialize: function () {
            this.el.on('click', this._onClick.bind(this));
        },
        _onClick(event) {
            event.preventDefault();

            this.el.parent().remove()

            var visualizations = $('.internal-dashboard-viz-container-items').children();

            $.each(visualizations, function(i, item) {
                item = $(item);
                item.attr('data-viz-position', i + 1);
                item.find('.internal-dashboard-viz-container-item-header').text((i + 1) + '.')
                item.find('label[for*=research_question]').attr('for', 'research_question_' + (i + 1))
                item.find('label[for*=visualization]').attr('for', 'visualization_' + (i + 1))
                item.find('label[for*=size]').attr('for', 'size_' + (i + 1))

                var rqSelect = item.find('select[id*=research_question]')
                rqSelect.attr('id', 'research_question_' + (i + 1))
                rqSelect.attr('name', 'research_question_' + (i + 1))
                rqSelect.attr('data-module-position', i + 1)

                var vizSelect = item.find('select[id*=visualization]')
                vizSelect.attr('id', 'visualization_' + (i + 1))
                vizSelect.attr('name', 'visualization_' + (i + 1))
                vizSelect.attr('data-module-position', i + 1)

                var sizeSelect = item.find('select[id*=size]')
                sizeSelect.attr('id', 'size_' + (i + 1))
                sizeSelect.attr('name', 'size_' + (i + 1))
                sizeSelect.attr('data-module-position', i + 1)
            })

            this.sandbox.publish('knowledgehub:remove-viz');
        }
    }
});

