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

                var rqSelect = item.find('select[id*=research_question]')
                rqSelect.attr('id', 'research_question_' + (i + 1))
                rqSelect.attr('name', 'research_question_' + (i + 1))
                rqSelect.attr('data-module-position', i + 1)

                var vizSelect = item.find('select[id*=visualization]')
                vizSelect.attr('id', 'visualization_' + (i + 1))
                vizSelect.attr('name', 'visualization_' + (i + 1))
                vizSelect.attr('data-module-position', i + 1)
            })

            this.sandbox.publish('knowledgehub:remove-viz');
        }
    }
});
