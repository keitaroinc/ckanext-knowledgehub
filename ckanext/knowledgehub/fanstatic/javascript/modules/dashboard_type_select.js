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

This module handles selecting dashboard type. If it's `internal` it displays
UI for inserting an indicator, if it's `external` it displays an input to
enter the source.

*/
ckan.module('knowledgehub-dashboard-type-select', function ($) {
    return {
        initialize: function () {
            this.sourceField = $('#dashboard-edit-form').find('#field-source')
            this.visulizationsContainer = $('.internal-dashboard-viz-container');
            this.editForm = $('#dashboard-edit-form');
            this.research_questions = $('.research-questions');
            this.datasets = $('.datasets');
            this.el.on('change', this.selectType.bind(this));
        },
        selectType() {
            var typeValue = this.el.val();
            if (!typeValue) {
                this.sourceField.parent().parent().addClass('hidden');
                this.research_questions.addClass('hidden');
                this.datasets.addClass('hidden');
                this.visulizationsContainer.css({ display: 'none' });
                this.editForm.attr('novalidate', '')
            } else if (typeValue === 'internal') {
                this.sourceField.parent().parent().addClass('hidden');
                this.research_questions.addClass('hidden');
                this.datasets.addClass('hidden');
                this.visulizationsContainer.css({display: 'block'});
                this.editForm.removeAttr('novalidate')
            } else if (typeValue === 'external') {
                this.sourceField.parent().parent().removeClass('hidden');
                this.research_questions.removeClass('hidden');
                this.datasets.removeClass('hidden');
                this.visulizationsContainer.css({ display: 'none' });
                this.editForm.attr('novalidate', '')
            }
        }
    }
});

