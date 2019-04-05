/*

This modules handles displaying a visualization item

Options:
    - type (Type of the visualization item: chart)
    - colors (Pattern of colors)
    - x_axis (Column name of x axis)
    - y_axis (Column name of y axis)
    - chart_type (What type of chart needs to be rendered)
    - title (Chart title)
    - show_legend ( Display or hide charts legend)
    - x_text_rotate ( Display text horizontal or vertical)
    - x_text_multiline ( Display the x axis text in one line or multiline)
    - tooltip_name (Title of the tooltip)
    - data_format (Charts data format e.g 2k, $2000, 2000.0, 2000.00)
    - y_tick_format (Y axis data format e.g 2k, $2000, 2000.0, 2000.00)
    - chart_padding_top (Add chart padding from the outside)
    - chart_padding_bottom (Add chart padding from the outside)
    - padding_top (Add charts padding)
    - padding_bottom (Add charts padding)
    - show_labels (Display or hide charts labels)
    - y_label (Aditional label added in y axis)
    - data_sort (Sort data, asc or desc)
    - category_name (The value of the chart category)

*/
'use strict';
ckan.module('chart', function() {
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
        initialize: function() {
            var newSql = this.create_sql();

            this.get_resource_datа(newSql);

            var chartField = $('.chart_field');

            // The Update chart button is only in the admin area. In the public
            // updating of viz items will be applied with a reload of the page.
            if (chartField.length > 0) {
                var updateBtn = chartField.find('.update-chart-btn');
                var deleteBtn = chartField.find('.delete-chart-btn');

                updateBtn.click(this.updateChart.bind(this));
                deleteBtn.click(this.deleteChart.bind(this));
            }

            this.sandbox.subscribe('querytool:updateCharts', this.updateChart.bind(this));
        },
        // Enhance the SQL query with grouping and only select 2 columns.
        create_sql: function() {
            var sqlString = $('#sql-string').val() ? $('#sql-string').val() : this.options.sql_string;
            console.log(sqlString);
            var parsedSqlString = sqlString.split('*');
            var sqlStringExceptSelect = parsedSqlString[1];
            // We need to encode some characters, eg, '+' sign:
            sqlStringExceptSelect = sqlStringExceptSelect.replace('+', '%2B');
            var sql = 'SELECT ' + '"' + this.options.x_axis + '", SUM("' + this.options.y_axis + '") as ' + '"' + this.options.y_axis + '"' + sqlStringExceptSelect + ' GROUP BY "' + this.options.x_axis + '"';

            return sql
        },
        // Get the data from Datastore.
        get_resource_datа: function(sql) {
            var category = (this.options.category_name === true) ? '' : this.options.category_name;
            var x_axis = (this.options.x_axis === true) ? '' : this.options.x_axis;
            var y_axis = (this.options.y_axis === true) ? '' : this.options.y_axis;
            var resource_id = sql.split('FROM')[1].split('WHERE')[0].split('"')[1];
            var dynamic_reference_type = (this.options.dynamic_reference_type === true) ? '' : this.options.dynamic_reference_type;
            var dynamic_reference_factor = (this.options.dynamic_reference_factor === true) ? '' : this.options.dynamic_reference_factor;

            var form_filters = this.getFilters();
            var options_filters = this.options.filters;
            var filters = form_filters.length ? form_filters : options_filters;
            console.log(sql);
            console.log(category);
            console.log(filters);

            if (x_axis && y_axis) {
                if (x_axis === y_axis) {
                    this.el.text(this._('X axis dimension cannot be same as Y axis dimension, please choose different one!'));
                } else {
                    api.post('get_chart_data', {
                        sql_string: sql,
                        category: category,
                        x_axis: x_axis,
                        y_axis: y_axis,
                        resource_id: resource_id,
                        filters: JSON.stringify(filters)
                    })
                    .done(function(data) {
                        if (data.success) {
                            this.fetched_data = data.result;

                            // Reset all metrics
                            this.y_axis_max = null;
                            this.y_axis_avg = null;
                            this.y_axis_min = null;
                            this.dynamic_reference_value = null;

                            // Get max/avg/min
                            if (category) {
                                this.y_axis_max = this.fetched_data.y_axis_max;
                                this.y_axis_avg = this.fetched_data.y_axis_avg;
                                this.y_axis_min = this.fetched_data.y_axis_min;
                                delete this.fetched_data.y_axis_max;
                                delete this.fetched_data.y_axis_avg;
                                delete this.fetched_data.y_axis_min;
                            } else {
                                var values = [];
                                for (var row of this.fetched_data) {
                                    // Values from server are strings..
                                    values.push(+row[y_axis.toLowerCase()]);
                                }
                                this.y_axis_max = Math.max.apply(null, values);
                                this.y_axis_avg = values.reduce(function (a, b) { return a + b; }, 0) / values.length;
                                this.y_axis_min = Math.min.apply(null, values);
                            }

                            // Dynamic reference
                            if (dynamic_reference_type) {
                                if (dynamic_reference_type === 'Maximum') {
                                    this.dynamic_reference_value = this.y_axis_max;
                                } else if (dynamic_reference_type === 'Average') {
                                    this.dynamic_reference_value = this.y_axis_avg;
                                } else if (dynamic_reference_type === 'Minimum') {
                                    this.dynamic_reference_value = this.y_axis_min;
                                }
                                if (dynamic_reference_factor !== '') {
                                    this.dynamic_reference_value = this.dynamic_reference_value * dynamic_reference_factor;
                                }
                            }
                            this.createChart(this.fetched_data);
                        } else {
                            this.el.text(this._('Chart could not be created!'));
                        }
                    }.bind(this));
                }
            } else {
                this.el.text(this._('Please choose X and Y axis dimensions and press Update!'));
            }
        },
        createChart: function(data) {
            var x_axis = this.options.x_axis.toString().toLowerCase();
            var y_axis = this.options.y_axis.toString().toLowerCase();
            var records = data;
            var show_legend = this.options.show_legend;
            var x_text_rotate = this.options.x_text_rotate;
            var x_text_multiline = this.options.x_text_multiline;
            var tooltip_name = this.options.tooltip_name;
            var data_format = this.options.data_format;
            var y_tick_format = this.options.y_tick_format;
            var tick_count = (this.options.tick_count === true) ? '' : this.options.tick_count;
            var show_labels = this.options.show_labels;
            var y_label = (this.options.y_label === true) ? null : this.options.y_label;
            var y_label_hide = this.options.y_label_hide;
            var y_from_zero = this.options.y_from_zero;
            var data_sort = this.options.data_sort;
            var measure_label = this.options.measure_label.toString().toLowerCase();
            var additionalCategory = (this.options.category_name === true) ? '' : this.options.category_name;
            var dynamic_reference_label = (this.options.dynamic_reference_label === true) ? '' : this.options.dynamic_reference_label;
            var values;

            // Base options
            var options = {
                bindto: this.el[0],
                color: {
                    pattern: this.options.colors.split(',')
                },
                padding: {
                    right: 50,
                    bottom:14
                }
            };

            // Title
            var titleVal = (this.options.title === true) ? '' : this.options.title;
            titleVal = this.renderChartTitle(titleVal, {
                measure: {name: y_axis, alias: measure_label},
                filters: [],
                optionalFilter: undefined,
            });
            options.title = {
                text: titleVal,
                position: "upper-left",
                padding: {
                    left: 0,
                    right: 0,
                    bottom: 15,
                    top:0
                }
            }
            options.legend = {
                show: show_legend
            }
            options.tooltip = {
                format: {}
            }

            // Y-label
            var y_label_text = !y_label_hide ? (y_label || measure_label || '') : '';

            // Sort data
            var sBarOrder = data_sort;
            if((this.options.chart_type !== 'sbar' ||
              this.options.chart_type !== 'shbar') && !additionalCategory){
              this.sortData(data_sort, records, y_axis, x_axis);
            }

            // Legend/tooltip
            options.legend = {show: show_legend}
            options.tooltip = {format: {}}
            if (tooltip_name !== true && tooltip_name !== '') {
                options.tooltip.format['title'] = function(d) {
                    if (options.data.type === 'donut' || options.data.type === 'pie') {
                        return tooltip_name;
                    }
                    return tooltip_name + ' ' + d;
                }
            }
            options.tooltip.format['value'] = function(value, ratio, id) {
                var dataf = this.sortFormatData(data_format, value);
                return dataf;
            }.bind(this);

            // Chart types
            if (this.options.chart_type === 'donut' ||
                this.options.chart_type === 'pie') {
                values = records.map(function(item) {
                    return [item[x_axis], item[y_axis]]
                });
                options.data = {
                    columns: values,
                    type: this.options.chart_type
                };
            } else if (this.options.chart_type === 'sbar' ||
                this.options.chart_type === 'shbar') {
                var horizontal = (this.options.chart_type === 'shbar') ? true : false

                var yrotate = 0;
                if (horizontal) {
                    // On horizontal bar the x axis is now actually the y axis
                    yrotate = x_text_rotate;
                }
                values = records.map(function(item) {
                    return [item[x_axis], item[y_axis]]
                });
                options.data = {
                    columns: values,
                    type: 'bar',
                    order: sBarOrder
                };
                var groups = values.map(function(item) {
                    return item[0];
                });
                options.data.groups = [groups];

                options.axis = {
                    rotated: horizontal,
                    y: {
                        tick: {
                            count: tick_count,
                            format: function(value) {
                                var dataf = this.sortFormatData(y_tick_format, value);
                                return dataf;
                            }.bind(this),
                            rotate: yrotate
                        },
                        padding: {
                            top: 50,
                            bottom: 50,
                        }
                    },
                    x: {
                        tick: {
                            rotate: x_text_rotate,
                            multiline: x_text_multiline,
                            multilineMax: 3,
                        }
                    }
                }
            } else {
                var rotate = false;
                var ctype = this.options.chart_type;
                var yrotate = 0;
                if (this.options.chart_type === 'hbar') {
                    rotate = true;
                    ctype = 'bar';
                    // On horizontal bar the x axis is now actually the y axis
                    yrotate = x_text_rotate;

                    //Resolving bug of bars with 2 columns
                    if(records.length==2){
                        options.padding = {
                        left:110
                      }
                    }
                }
                if (this.options.chart_type === 'bscatter') {
                    //workaround for bubble charts, scale log base 10 because of large values
                    var rs = d3.scale.log().base(10).domain([1, 1000]).range([0, 10]);
                    ctype = 'scatter';
                    options.point = {
                        r: function(d) {
                            var num = d.value;
                            return rs(num)
                        },
                        sensitivity: 100,
                        focus: {
                            expand: {
                                enabled: true
                            }
                        }
                    };
                }

                var columns = [];

                if (additionalCategory) {

                    var orderedRecords = {};
                    Object.keys(records).sort().forEach(function(key) {
                        orderedRecords[key] = records[key];
                    });

                    for (var key in orderedRecords) {
                        columns.push(orderedRecords[key]);;
                    }

                    options.data = {
                        x: 'x',
                        columns: columns,
                        type: ctype,
                        labels: show_labels
                    };
                } else {
                    columns = records.map(function(item) {
                        return Number(item[y_axis]);
                    });

                    var categories = records.map(function(item) {
                        return item[x_axis];
                    });

                    columns.unshift(this.options.x_axis);

                    options.data = {
                        columns: [columns],
                        type: ctype,
                        labels: show_labels
                    };

                }

                if (show_labels) {
                    options.data['labels'] = {
                        format: function(value) {
                            var dataf = this.sortFormatData(data_format, value);
                            return dataf;
                        }.bind(this),
                    }
                }

                //Tick count on x-axis for line charts
                if (this.options.chart_type === 'line') {
                    options.axis = {
                        y: {
                            tick: {
                                count: tick_count,
                                format: function(value) {
                                    var dataf = this.sortFormatData(y_tick_format, value);
                                    return dataf;
                                }.bind(this),
                                rotate: yrotate
                            },
                            padding: {
                                top: 50,
                                bottom: 50,
                            },
                            label: {
                              text: y_label_text,
                              position: 'outer-middle',
                            }
                        },
                        x: {
                            type: 'category',
                            categories: categories,
                            tick: {
                                count:5,
                                rotate: x_text_rotate,
                                multiline: x_text_multiline,
                                multilineMax: 3
                            }
                        },
                        rotated: rotate,
                    };
                } else {
                  //no Tick count on x-axis for bar
                  options.axis = {
                      y: {
                          tick: {
                              count: tick_count,
                              format: function(value) {
                                  var dataf = this.sortFormatData(y_tick_format, value);
                                  return dataf;
                              }.bind(this),
                              rotate: yrotate
                          },
                          padding: {
                              top: 50,
                              bottom: 50,
                          },
                          label: {
                            text: y_label_text,
                            position: 'outer-middle',
                          }
                      },
                      x: {
                          type: 'category',
                          categories: categories,
                          tick: {
                              rotate: x_text_rotate,
                              multiline: x_text_multiline,
                              multilineMax: 3
                          }
                      },
                      rotated: rotate,
                  };

                }
                options.point = {
                  r: 3,
                }
            }

            // Reference lines
            if (!['sbar', 'shbar', 'donut', 'pie'].includes(this.options.chart_type)) {
                options.grid = {y: {lines: []}};

                // Dynamic
                if (this.dynamic_reference_value) {
                    // Base
                    options.grid.y.lines.push({
                        value: this.dynamic_reference_value,
                        text: dynamic_reference_label,
                        class: 'base',
                    })
                    // Active (to show on hover)
                    let value = this.sortFormatData(data_format, this.dynamic_reference_value)
                    options.grid.y.lines.push({
                        value: this.dynamic_reference_value,
                        text: dynamic_reference_label + ' (' + value + ')',
                        class: 'active html2canvas-ignore',
                    })
                }

                // Y axis range
                if (this.dynamic_reference_value) {
                    options.axis.y.min = Math.min.apply(null, [this.dynamic_reference_value, this.y_axis_min].filter(function (value) {return !isNaN(value);}));
                    options.axis.y.max = Math.max.apply(null, [this.dynamic_reference_value, this.y_axis_max].filter(function (value) {return !isNaN(value);}));
                    options.axis.y.padding = {bottom: 50, top: 50};
                    if (['bar', 'hbar'].includes(this.options.chart_type)) {
                        options.axis.y.padding.bottom = 0;
                    }
                }
            }

            // Y-axis from zero
            if (['line', 'area', 'area-spline', 'spline', 'scatter', 'bscatter'].includes(this.options.chart_type)) {
              if (y_from_zero) {
                options.axis.y.min = 0;
                options.axis.y.padding = options.axis.y.padding || {};
                options.axis.y.padding.bottom = 0;
              }
            }

            // Generate chart
            var chart = c3.generate(options);
        },
        // Get the values from dropdowns and rerender the chart.
        updateChart: function() {
            var chartField = $('.chart_field');

            var chartTypeSelect = chartField.find('[name*=chart_field_type]');
            var chartTypeValue = chartTypeSelect.val();

            var colorSelect = chartField.find('[name*=chart_field_color]');
            var colorValue = colorSelect.val();

            var chartPaddingLeft = chartField.find('input[name*=chart_field_chart_padding_left]');
            var chartPaddingLeftVal = chartPaddingLeft.val();

            var chartPaddingBottom = chartField.find('input[name*=chart_field_chart_padding_bottom]');
            var chartPaddingBottomVal = chartPaddingBottom.val();

            var axisXSelect = chartField.find('[name*=chart_field_x_axis_column]');
            var axisXValue = axisXSelect.val();

            var axisYSelect = chartField.find('[name*=chart_field_y_axis_column]');
            var axisYValue = axisYSelect.val();

            var categoryName = chartField.find('[name*=chart_field_category_name]');
            var categoryNameVal = categoryName.val();

            var chartTitle = chartField.find('input[name*=chart_field_title]');
            var chartTitleVal = chartTitle.val();

            var legend = chartField.find('input[name*=chart_field_legend]');
            var legendVal = legend.is(':checked');

            var xTextRotate = chartField.find('[name*=chart_field_x_text_rotate]');
            var xTextRotateVal = xTextRotate.val();

            var xTextMultiline = chartField.find('[name*=chart_field_x_text_multiline]');
            var xTextMultilineVal = xTextMultiline.is(':checked');

            var tooltipName = chartField.find('input[name*=chart_field_tooltip_name]');
            var tooltipNameVal = tooltipName.val();

            var dataFormat = chartField.find('[name*=chart_field_data_format]');
            var dataFormatVal = dataFormat.val();

            var yTickFormat = chartField.find('[name*=chart_field_y_ticks_format]');
            var yTickFormatVal = yTickFormat.val();

            var paddingTop = chartField.find('input[name*=chart_field_padding_top]');
            var paddingTopVal = paddingTop.val();

            var paddingBottom = chartField.find('input[name*=chart_field_padding_bottom]');
            var paddingBottomVal = paddingBottom.val();

            var tickCount = chartField.find('input[name*=chart_field_tick_count]');
            var tickCountVal = tickCount.val();

            var sortOpt = chartField.find('select[name*=chart_field_sort]');
            var sortVal = sortOpt.val();

            var dataLabels = chartField.find('input[name*=chart_field_labels]');
            var dataLabelsVal = dataLabels.is(':checked');

            var yLabbel = chartField.find('input[name*=chart_field_y_label]');
            var yLabbelVal = yLabbel.val();

            var yLabelHide = chartField.find('input[name*=chart_field_y_label_hide]');
            var yLabelHideVal = yLabelHide.is(':checked');

            var yFromZero = chartField.find('input[name*=chart_field_y_from_zero]');
            var yFromZeroVal = yFromZero.is(':checked');

            var dynamicReferenceType = chartField.find('select[name*=chart_field_dynamic_reference_type]');
            var dynamicReferenceTypeVal = dynamicReferenceType.val();

            var dynamicReferenceFactor = chartField.find('input[name*=chart_field_dynamic_reference_factor]');
            var dynamicReferenceFactorVal = dynamicReferenceFactor.val();

            var dynamicReferenceLabel = chartField.find('input[name*=chart_field_dynamic_reference_label]');
            var dynamicReferenceLabelVal = dynamicReferenceLabel.val();

            var measureLabelVal = $('#chart_field_y_axis_column option:selected').text().toLowerCase();

            this.options.colors = colorValue;
            this.options.chart_type = chartTypeValue;
            this.options.x_axis = axisXValue;
            this.options.y_axis = axisYValue;
            this.options.title = chartTitleVal;
            this.options.show_legend = legendVal;
            this.options.x_text_rotate = xTextRotateVal;
            this.options.x_text_multiline = xTextMultilineVal;
            this.options.tooltip_name = tooltipNameVal;
            this.options.data_format = dataFormatVal;
            this.options.y_tick_format = yTickFormatVal;
            this.options.chart_padding_left = chartPaddingLeftVal;
            this.options.chart_padding_bottom = chartPaddingBottomVal;
            this.options.padding_top = paddingTopVal;
            this.options.padding_bottom = paddingBottomVal;
            this.options.show_labels = dataLabelsVal;
            this.options.tick_count = tickCountVal;
            this.options.y_label = yLabbelVal;
            this.options.y_label_hide = yLabelHideVal;
            this.options.y_from_zero = yFromZeroVal;
            this.options.category_name = categoryNameVal;
            this.options.data_sort = sortVal;
            this.options.dynamic_reference_type = dynamicReferenceTypeVal;
            this.options.dynamic_reference_factor = dynamicReferenceFactorVal;
            this.options.dynamic_reference_label = dynamicReferenceLabelVal;
            this.options.measure_label = measureLabelVal;
            var newSql = this.create_sql();

            this.get_resource_datа(newSql);
        },

        // Delete the current chart
        deleteChart: function() {
            $('.chart_field').remove();
        },

        teardown: function() {
            // We must always unsubscribe on teardown to prevent memory leaks.
            this.sandbox.unsubscribe('querytool:updateCharts', this.updateChart.bind(this));
        },

        getFilters: function() {
            var filter_items = $('#data-transformation-module').find('.filter_item');
            var filters = [];
            var name = '';
            var value = '';

            $.each(filter_items, function (idx, elem) {
                name = $(elem).find('[id*=data_filter_name_]').select2('val');
                value = $(elem).find('[id*=data_filter_value_]').select2('val');
                filters.push({
                    'name': name,
                    'value': value
                });
            });
            return filters;
        },

        sortData: function(data_sort, records, y_axis, x_axis) {
            if (data_sort === 'asc') {
                records.sort(function(a, b) {
                    return a[y_axis] - b[y_axis]
                });
            } else if (data_sort === 'desc') {
                records.sort(function(a, b) {
                    return a[y_axis] - b[y_axis]
                });
                records.reverse();
            } else {
                records.sort(function(a, b) {
                    var x = a[x_axis];
                    var y = b[x_axis];
                    if (!isNaN(x)) {
                        return Number(x) - Number(y);
                    } else {
                        if (x < y) //sort string ascending
                            return -1;
                        if (x > y)
                            return 1;
                        return 0; //default return value (no sorting)
                    }
                });
            }
        },

        // Format number
        sortFormatData: function(dataf, val) {
            var digits = 0;
            var format = '';
            // Currency
            if (dataf === '$') {
                // Add a coma for the thousands and limit the number of decimals to two:
                // $ 2,512.34 instead of $2512.3456
                digits = this.countDecimals(val, 2);
                format = d3.format('$,.' + digits + 'f');
            // Rounded
            } else if (dataf === 's') {
                // Limit the number of decimals to one: 2.5K instead of 2.5123456K
                val = Math.round(val*10) / 10;
                format = d3.format(dataf);
            // Others
            } else {
                format = d3.format(dataf);
            }
            return format(val);
        },

        // Count format decimals limited by "max"
        countDecimals: function (val, max) {
            return Math.min(val*10 % 1 ? 2 : val % 1 ? 1 : 0, max);
        },

        // Render dynamic chart titles
        renderChartTitle: function (title, options) {

            // Configure nunjucks
            var env = nunjucks.configure({tags: {variableStart: '{', variableEnd: '}'}});

            // Prepare data
            var data = {measure: options.measure.alias};
            for (let filter of options.filters) data[filter.slug] = filter.value;
            if (options.optionalFilter) data.optional_filter = options.optionalFilter.value;

            // Render and return
            try {
                    return env.renderString(title, data);
            } catch (error) {
                    return title;
            }
        },
    }
});
