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
            this.el.on('change', this.selectType.bind(this));
        },
        selectType() {
            var typeValue = this.el.val();
            if (!typeValue) {
                this.sourceField.parent().parent().addClass('hidden');
                this.research_questions.addClass('hidden');
                this.visulizationsContainer.css({ display: 'none' });
                this.editForm.attr('novalidate', '')
            } else if (typeValue === 'internal') {
                this.sourceField.parent().parent().addClass('hidden');
                this.research_questions.addClass('hidden');
                this.visulizationsContainer.css({display: 'block'});
                this.editForm.removeAttr('novalidate')
            } else if (typeValue === 'external') {
                this.sourceField.parent().parent().removeClass('hidden');
                this.research_questions.removeClass('hidden');
                this.visulizationsContainer.css({ display: 'none' });
                this.editForm.attr('novalidate', '')
            }
        }
    }
});
