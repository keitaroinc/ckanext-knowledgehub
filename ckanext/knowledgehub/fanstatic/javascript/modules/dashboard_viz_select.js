/*

This module handles displaying a visualization from a dropdown of resource views.

*/
ckan.module('knowledgehub-dashboard-viz-select', function ($) {
    return {
        initialize: function () {
            this.el.on('change', this._selectViz.bind(this));
            this.vizContainerItem = $('div[data-viz-position=' + this.options.position + ']').find('.internal-dashboard-viz-container-item-view');
        },
        _selectViz() {
            this.vizContainerItem.html('')

            if (!this.el.val()) {
                return;
            }

            var currentOption = this.el.find('option[value=' + this.el.val() + ']')
            var resView = currentOption.attr('data-resource-view')

            if (resView) {
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
