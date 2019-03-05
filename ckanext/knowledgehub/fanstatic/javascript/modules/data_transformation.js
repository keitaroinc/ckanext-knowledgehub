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
      resource_id = self.options.resourceId,
      fields = self.options.fields,
      dropdownTemplate = self.options.dropdownTemplate;
    self.el.find("#add-filter-button").click(function() {
      addFilter(self, resource_id, fields);
    });

  };

  function applyDropdown(self, inputField, filterName, resourceId) {

    var queryLimit = 20;

    inputField.select2({
      width: 'resolve',
      placeholder: self._('Select a value'),
      minimumInputLength: 0,
      ajax: {
        url: ckan.url('/api/3/action/datastore_search'),
        datatype: 'json',
        quietMillis: 200,
        cache: true,
        data: function(term, page) {
          var offset = (page - 1) * queryLimit,
            query;

          query = {
            resource_id: resourceId,
            limit: queryLimit,
            offset: offset,
            fields: filterName,
            distinct: true,
            sort: filterName,
            include_total: false
          };

          if (term !== '') {
            var q = {};
            if (term.indexOf(' ') == -1) {
              term = term + ':*';
              query.plain = false;
            }
            q[filterName] = term;
            query.q = JSON.stringify(q);
          }

          return query;
        },
        results: function(data, page) {
          var records = data.result.records,
            hasMore = (records.length == queryLimit),
            results;

          results = $.map(records, function(record) {
            return {
              id: record[filterName],
              text: String(record[filterName])
            };
          });

          return {
            results: results,
            more: hasMore
          };
        },
      },
      initSelection: function(element, callback) {
        var data = {
          id: element.val(),
          text: element.val()
        };
        callback(data);
      },
    });
  }

  function addFilter(self, resource_id, fields) {
    var filter_items = $('.filter_item');
    var total_items = filter_items.length + 1;

    api.getTemplate('filter_item.html', {
        fields: fields.toString(),
        n: total_items,
        resource_id: resource_id,
        class: 'hidden'
      })
      .done(function(data) {

        self.el.append(data);

        // Remove item event handler
        var removeMediaItemBtn = $('.remove-filter-item-btn');
        removeMediaItemBtn.on('click', function(e) {
          $(e.target).closest('.filter_item').remove();
          //                            _handleFilterItemsOrder();
        });

        handleRenderedFilters(self, total_items, resource_id, fields);

      });

  }

  function handleRenderedFilters(self, item_id, resource_id, fields) {

    var filter_name_select;
    var filter_value_select;
    var filter_value_select_id;

    if (item_id) {
      filter_name_select = $('[id=data_filter_name_' + item_id + ']');
    } else {
      filter_name_select = $('[id*=data_filter_name_]');
    }

    if (item_id) {
      filter_value_select = $('[id=data_filter_value_' + item_id + ']');
    } else {
      filter_value_select = $('[id*=data_filter_value_]');
    }


    var data = $.map(fields, function(d) {
      return {
        id: d,
        text: d
      };
    });

    filter_name_select.select2({
      data: data,
      placeholder: self._('Select a field'),
      width: 'resolve'
    })



    filter_name_select.change(function(event) {
      var elem = $(this);
      var filter_name = elem.val();
      console.log(filter_name);
      var filter_name_select_id = elem.attr('id');


      filter_value_select_id = filter_name_select_id.replace('name', 'value');
      $('.' + filter_value_select_id).removeClass('hidden');
      $('#' + filter_value_select_id).select2("val", "");

      applyDropdown(self, filter_value_select, filter_name, resource_id)

    });

  }

  return {
    initialize: initialize
  }
});