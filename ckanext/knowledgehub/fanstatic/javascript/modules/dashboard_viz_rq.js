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
            this.vizDropdown = this.el.parent().parent().parent().find('.internal-dashboard-viz-dropdown')
        },
        selectRQ() {
            var RQValue = this.el.val();

            if (RQValue) {
                api.get('visualizations_for_rq', { research_question: RQValue})
                    .done(function(data) {
                        if (data.success) {
                            this.vizDropdown.css({ display: 'block' });
                            if (data.result.length > 0) {
                                var select = this.vizDropdown.find('select');
                                select.append('<option value="" selected>Choose visualization</option>')
                                data.result.forEach(function(resView) {
                                    select.append('<option value="' + window.encodeURIComponent(JSON.stringify(resView)) + '">' + resView.title + '</option>');
                                })
                            }
                        } else {
                            alert(this._('Could not get visualizations for research question: ' + RQValue));
                        }
                    }.bind(this))
            } else {
                this.vizDropdown.css({display: 'none'});
            }
        }
    }
});
