/*

This module handles displaying a visualization from a dropdown of resource views.

*/
ckan.module('knowledgehub-dashboard-viz-select', function ($) {
    return {
        initialize: function () {
            this.el.on('change', this._selectViz.bind(this));
        },
        _selectViz() {
            var resView = this.el.val()

            if (resView) {
                resView = JSON.parse(window.decodeURIComponent(resView))
                this.sandbox.client.getTemplate('chart_module.html',
                    resView.__extras,
                    this._onReceiveSnippet.bind(this)
                );
                console.log(resView)
            } else {
                // hide viz
            }
        },
        _onReceiveSnippet(html) {
            var vizContainerItem = $('.internal-dashboard-viz-container-item_' + this.options.position).find('.internal-dashboard-viz-container-item-view');
            vizContainerItem.append(html)
            var resViewModule = vizContainerItem.find('div[data-module]')
            console.log(resViewModule)
            window.ckan.module.initializeElement(resViewModule[0]);
        }
    }
});
