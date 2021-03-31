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
    },
    // function for dynamic sorting
    compareValues: function(key, order) {
      return function(a, b) {
        if (!a.hasOwnProperty(key) || !b.hasOwnProperty(key)) {
          // property doesn't exist on either object
          return 0;
        }
        const varA = (typeof a[key] === 'string') ?
          a[key].toUpperCase() : a[key];
        const varB = (typeof b[key] === 'string') ?
          b[key].toUpperCase() : b[key];

        let comparison = 0;
        if (varA > varB) {
          comparison = 1;
        } else if (varA < varB) {
          comparison = -1;
        }
        return (
          (order == 'desc') ? (comparison * -1) : comparison
        );
      };
    }
  }

  function _handleFilterItemsOrder() {

    var filter_items = $('.filter_item');

    $.each(filter_items, function(i, item) {
      item = $(item);

      var order = i + 1;
      var removeFilterButton = item.find('[id*=remove_filter_item_btn_]');
      var selectFilterName = item.find('[id*=data_filter_name_]');
      var selectFilterValue = item.find('[id*=data_filter_value_]');
      var inputFilterAndOperator = item.find('[id*=data_filter_operator_and_]');
      var labelFilterAndOperator = item.find('label[for*=data_filter_operator_and_]');
      var inputFilterOrOperator = item.find('[id*=data_filter_operator_or_]');
      var labelFilterOrOperator = item.find('label[for*=data_filter_operator_or_]');

      item.attr('id', 'filter_item_' + order);

      removeFilterButton.attr('id', 'remove_filter_item_btn_' + order);

      selectFilterName.attr('id', 'data_filter_name_' + order);
      selectFilterName.attr('name', 'data_filter_name_' + order);

      selectFilterValue.attr('id', 'data_filter_value_' + order);
      selectFilterValue.attr('name', 'data_filter_value_' + order);

      inputFilterAndOperator.attr('id', 'data_filter_operator_and_' + order);
      inputFilterAndOperator.attr('name', 'data_filter_operator_' + order);
      labelFilterAndOperator.attr('for', 'data_filter_operator_and_' + order);

      inputFilterOrOperator.attr('id', 'data_filter_operator_or_' + order);
      inputFilterOrOperator.attr('name', 'data_filter_operator_' + order);
      labelFilterOrOperator.attr('for', 'data_filter_operator_or_' + order);

      if (order == 1) {
        item.find('.filter-operator').remove();
      }
    });
  }

  function _getFilters() {

    var filter_items = $('#data-transformation-module').find('.filter_item');
    var filters = [];
    var operator = '';
    var name = '';
    var value = '';

    $.each(filter_items, function(idx, elem) {

      operator = $(elem).find('input[name*=data_filter_operator_]:checked').val();
      name = $(elem).find('[id*=data_filter_name_]').select2('val');
      value = $(elem).find('[id*=data_filter_value_]').select2('val');
      filters.push({
        'operator': operator,
        'name': name,
        'value': value
      });
    });
    return filters;
  }

  function _generateWhereClause(filters) {
    var where_clause = '';

    if (filters.length > 1) {

      filters.forEach(function(filter, index) {

        var name = filter['name'];
        var value = filter['value'];

        if (name && value) {
          if (index === 0) {

            where_clause = 'WHERE ("' + name + '" = \'' + value + '\')';

          } else {
            var operator = filter['operator'];
            where_clause += ' ' + operator + ' ("' + name + '" = \'' + value + '\')';
          }
        }
      });

    } else if (filters.length == 1) {

      var filter = filters[0];
      var name = filter['name'];
      var value = filter['value'];
      if (name && value) {
        where_clause = 'WHERE ("' + name + '" = \'' + value + '\')';
      }
    }
    return where_clause;
  }

  function generateSql(resource_id, filters) {

    var where_clause = _generateWhereClause(filters)
    var sql = 'SELECT * FROM "' + resource_id + '" ' + where_clause + '';
    $('#sql-string').val(sql);
    console.log(sql);
    return sql;
  }

  function addFilter(self, resource_id, fields, filter) {

    return new Promise(function(resolve, reject) {

      var total_items = 0;

      if (filter) {
        total_items = filter['order'];
      } else {
        var filter_items = $('#data-transformation-module').find('.filter_item');
        total_items = filter_items.length + 1;
      }

      api.getTemplate('filter_item.html', {
          n: total_items,
          class: 'hidden'
        })
        .done(function(data) {

          self.el.append(data);

          // Remove item event handler
          var removeMediaItemBtn = $('#remove_filter_item_btn_' + total_items);
          removeMediaItemBtn.on('click', function(e) {
            $(e.target).closest('.filter_item').remove();
            _handleFilterItemsOrder();
            var filters = _getFilters();
            var sql = generateSql(resource_id, filters);
            ckan.sandbox().publish('knowledgehub:updateMap');
          });

          handleRenderedFilter(self, total_items, resource_id, fields, filter);
          resolve('filter rendering finished');
        });
    });
  }

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

  function handleRenderedFilter(self, item_id, resource_id, fields, filter) {

    var filter_operator;
    var filter_name_select;
    var filter_value_select;
    var filter_value_select_id;

    if (item_id) {
      filter_name_select = $('[id=data_filter_name_' + item_id + ']');
      filter_value_select = $('[id=data_filter_value_' + item_id + ']');
      filter_operator = $('[name=data_filter_operator_' + item_id + ']');

    } else {
      filter_name_select = $('[id*=data_filter_name_]');
      filter_value_select = $('[id*=data_filter_value_]');
      filter_operator = $('[id=data_filter_operator_]');
    }

    var filter_name_select_data = $.map(fields, function(d) {
      return {
        id: d,
        text: d
      };
    });

    filter_name_select.select2({
      data: filter_name_select_data,
      placeholder: self._('Select a field'),
      width: 'resolve'
    })

    if (filter) {

      var filter_name_select_id = filter_name_select.attr('id');
      filter_value_select_id = filter_name_select_id.replace('name', 'value');

      //    Set appropriate filter operator checked
      if (filter.operator) {
        var filter_operator_button_id = filter_name_select_id.replace('name', 'operator_' + filter.operator.toLowerCase());
        $('#' + filter_operator_button_id).attr('checked', 'checked');
      }

      //    Set appropriate filter name as selected
      filter_name_select.select2('val', filter['name']);

      //    Initialize filter value select to get values for the selected filter name
      applyDropdown(self, filter_value_select, filter['name'], resource_id);
      filter_value_select.select2('val', filter['value']);

      $('.' + filter_value_select_id).removeClass('hidden');

    }

    filter_name_select.change(function(event) {
      var elem = $(this);
      var filter_name = elem.val();
      var filter_name_select_id = elem.attr('id');


      filter_value_select_id = filter_name_select_id.replace('name', 'value');
      $('#' + filter_value_select_id).select2('val', '');

      applyDropdown(self, filter_value_select, filter_name, resource_id);

      $('.' + filter_value_select_id).removeClass('hidden');

    });

    filter_value_select.change(function(event) {

      var elem = $(this);
      filter_value_select_id = elem.attr('id');

      var filters = _getFilters();
      var sql = generateSql(resource_id, filters);
      ckan.sandbox().publish('knowledgehub:updateMap');
    });

    filter_operator.change(function() {
      var filters = _getFilters();
      var sql = generateSql(resource_id, filters);
      ckan.sandbox().publish('knowledgehub:updateMap');
    });
  }

  function initialize() {
    var self = this,
      resource_id = self.options.resourceId,
      fields = self.options.fields,
      filters = self.options.filters;

    self.el.find("#add-filter-button").click(function() {
      addFilter(self, resource_id, fields).then(function(result) {
//        console.log('New' + result);
      });
    });
    if (filters.length) {
      // Generate and render existing filters in appropriate order
      filters.sort(api.compareValues('order', 'asc'));
      var f = addFilter(self, resource_id, fields, filters[0]);

      for (var i = 1; i < filters.length; i++) {
        f = f.then(addFilter(self, resource_id, fields, filters[i]));
      }
    }

  }

  return {
    initialize: initialize
  }
});