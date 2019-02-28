ckan.module('data-transformation', function($) {
  'use strict';

  var api = {
    get: function(action, params, async) {
      var api_ver = 3;
      var base_url = ckan.sandbox().client.endpoint;
      params = $.param(params);
      var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
      if (!async) {
        $.ajaxSetup({
          async: false
        });
      }
      return $.getJSON(url);
    },
    post: function(action, data, async) {
      var api_ver = 3;
      var base_url = ckan.sandbox().client.endpoint;
      var url = base_url + '/api/' + api_ver + '/action/' + action;
      if (!async) {
        $.ajaxSetup({
          async: false
        });
      }
      return $.post(url, JSON.stringify(data), 'json');
    },
    getTemplate: function(filename, params, success, error) {

      var locale = $('html').attr('lang');
      var url = ckan.url(locale + '/api/1/util/snippet/' + encodeURIComponent(filename));

      // Allow function to be called without params argument.
      if (typeof params === 'function') {
        error = success;
        success = params;
        params = {};
      }

      return $.get(url, params || {}).then(success, error);
    }
  };

  function initialize() {
    var self = this,
      resourceId = self.options.resourceId,
      fields = self.options.fields,
      dropdownTemplate = self.options.dropdownTemplate;
    console.log(self.el);

  };

  function addFilter() {

  }

  return {
    initialize: initialize
  }
});