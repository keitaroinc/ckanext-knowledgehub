/*

This modules handles displaying a visualization item

Options:
    sql_string (The SQL query with predifined filters if any)
    resource_id (The ID of the resource)
    resource_name (The name of the indicator)
    y_axis (Measure of the table)
    main_value (The dimension)
    category_name (The value of the table category)
    data_type (Can be quantitative or qualitative)
    data_format (Format of the data in the table)
    table_title (Table title)

*/
"use strict";
ckan.module('table', function () {

    // Languages for datables
    var LANGUAGES = {
        'en': {
            "sProcessing": "Processing...",
            "sLengthMenu": "Show _MENU_ records",
            "sZeroRecords": "No results found",
            "sEmptyTable": "No data available in this table",
            "sInfo": "Showing records from _START_ to _END_ of a total of _TOTAL_ records",
            "sInfoEmpty": "Showing records from 0 to 0 of a total of 0 records",
            "sInfoFiltered": "(filtering a total of _MAX_ records)",
            "sInfoPostFix": "",
            "sSearch": "Search for:",
            "sUrl": "",
            "sInfoThousands": ",",
            "sLoadingRecords": "Loading...",
            "oPaginate": {
                "sFirst": "First",
                "sLast": "Latest",
                "sNext": "Following",
                "sPrevious": "Previous"
            },
            "oAria": {
                "sSortAscending": ": Activate to order the column ascending",
                "sSortDescending": ": Activate to order the column in descending order"
            }
        },
        'es': {
            "sProcessing": "Procesando...",
            "sLengthMenu": "Mostrar _MENU_ registros",
            "sZeroRecords": "No se encontraron resultados",
            "sEmptyTable": "Ningún dato disponible en esta tabla",
            "sInfo": "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
            "sInfoEmpty": "Mostrando registros del 0 al 0 de un total de 0 registros",
            "sInfoFiltered": "(filtrado de un total de _MAX_ registros)",
            "sInfoPostFix": "",
            "sSearch": "Buscar:",
            "sUrl": "",
            "sInfoThousands": ",",
            "sLoadingRecords": "Cargando...",
            "oPaginate": {
                "sFirst": "Primero",
                "sLast": "Último",
                "sNext": "Siguiente",
                "sPrevious": "Anterior"
            },
            "oAria": {
                "sSortAscending": ": Activar para ordenar la columna de manera ascendente",
                "sSortDescending": ": Activar para ordenar la columna de manera descendente"
            }
        },
        'fr': {
            "sProcessing": "Traitement en cours...",
            "sSearch": "Rechercher&nbsp;:",
            "sLengthMenu": "Afficher _MENU_ &eacute;l&eacute;ments",
            "sInfo": "Affichage de l'&eacute;l&eacute;ment _START_ &agrave; _END_ sur _TOTAL_ &eacute;l&eacute;ments",
            "sInfoEmpty": "Affichage de l'&eacute;l&eacute;ment 0 &agrave; 0 sur 0 &eacute;l&eacute;ment",
            "sInfoFiltered": "(filtr&eacute; de _MAX_ &eacute;l&eacute;ments au total)",
            "sInfoPostFix": "",
            "sLoadingRecords": "Chargement en cours...",
            "sZeroRecords": "Aucun &eacute;l&eacute;ment &agrave; afficher",
            "sEmptyTable": "Aucune donn&eacute;e disponible dans le tableau",
            "oPaginate": {
                "sFirst": "Premier",
                "sPrevious": "Pr&eacute;c&eacute;dent",
                "sNext": "Suivant",
                "sLast": "Dernier"
            },
            "oAria": {
                "sSortAscending": ": activer pour trier la colonne par ordre croissant",
                "sSortDescending": ": activer pour trier la colonne par ordre d&eacute;croissant"
            },
            "select": {
                "rows": {
                    _: "%d lignes séléctionnées",
                    0: "Aucune ligne séléctionnée",
                    1: "1 ligne séléctionnée"
                }
            }
        },
        'pt_BR': {
            "sEmptyTable": "Nenhum registro encontrado",
            "sInfo": "Mostrando de _START_ até _END_ de _TOTAL_ registros",
            "sInfoEmpty": "Mostrando 0 até 0 de 0 registros",
            "sInfoFiltered": "(Filtrados de _MAX_ registros)",
            "sInfoPostFix": "",
            "sInfoThousands": ".",
            "sLengthMenu": "_MENU_ resultados por página",
            "sLoadingRecords": "Carregando...",
            "sProcessing": "Processando...",
            "sZeroRecords": "Nenhum registro encontrado",
            "sSearch": "Pesquisar",
            "oPaginate": {
                "sNext": "Próximo",
                "sPrevious": "Anterior",
                "sFirst": "Primeiro",
                "sLast": "Último"
            },
            "oAria": {
                "sSortAscending": ": Ordenar colunas de forma ascendente",
                "sSortDescending": ": Ordenar colunas de forma descendente"
            }
        },
        'zh_CN': {
            "sProcessing": "处理中...",
            "sLengthMenu": "显示 _MENU_ 项结果",
            "sZeroRecords": "没有匹配结果",
            "sInfo": "显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",
            "sInfoEmpty": "显示第 0 至 0 项结果，共 0 项",
            "sInfoFiltered": "(由 _MAX_ 项结果过滤)",
            "sInfoPostFix": "",
            "sSearch": "搜索:",
            "sUrl": "",
            "sEmptyTable": "表中数据为空",
            "sLoadingRecords": "载入中...",
            "sInfoThousands": ",",
            "oPaginate": {
                "sFirst": "首页",
                "sPrevious": "上页",
                "sNext": "下页",
                "sLast": "末页"
            },
            "oAria": {
                "sSortAscending": ": 以升序排列此列",
                "sSortDescending": ": 以降序排列此列"
            }
        },
    };

    // CKAN API gateway
    var api = {
        get: function (action, params, callback) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            $.getJSON(url, callback);
        },
        post: function (action, data) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, JSON.stringify(data), 'json');
        },
        url: function (action, params) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            return url;
        }

    };

    // Create module
    return {
        initialize: function () {

            this.createTable();

            var tableField = this.el.closest('.table_item');

            // The Update table button is only in the admin area. In the public
            // updating of tables will be applied with a reload of the page.
            if (tableField.length > 0) {
                var updateBtn = tableField.find('.update-table-btn');

                updateBtn.click(this.updateTable.bind(this));
            }

            this.sandbox.subscribe('knowledgehub:updateTables', this.updateTable.bind(this));
        },

        createTable: function (yVal, xVal, fromUpdate) {
            var module = this;
            // Prepare settings
            var locale = $('html').attr('lang');

            var y_axis = (yVal) ? yVal : this.options.y_axis;
            var main_value = (xVal) ? xVal : this.options.main_value;
            if (fromUpdate) main_value = xVal;
            var category_name = (this.options.category_name === true) ? '' : this.options.category_name;
            var data_type = (this.options.data_type === true) ? 'quantitative' : this.options.data_type;
            var title = (this.options.table_title === true) ? '' : this.options.table_title;
            var filename_export = (title === '') ? this.options.resource_name : title;

            filename_export = filename_export.split('.').slice(0, 1).join('.');

            this.el.text('');
            if (main_value === true || y_axis === true) {
                this.el.text(this._('Please choose X and Y axis dimensions and press Update!'));
                return;
            }

            // Get data and create table
            var sql_string = this.create_sql_string(main_value, y_axis, category_name, data_type);
            api.get('get_resource_data', { sql_string: sql_string }, function (response) {

                if (response.success) {
                    var rows = response.result;

                    // Render table HTML
                    var html = '';
                    if (data_type === 'qualitative') {
                        html = module.render_qualitative_data_table(rows, main_value);
                    } else if (category_name) {
                        html = module.render_data_table_with_category(rows, category_name, main_value, y_axis);
                    } else {
                        html = module.render_data_table(rows, main_value, y_axis);
                    }

                    var table = module.el.next('#table-item-' + module.options.resource_id);
                    // Enable jquery.datatable
                    if ($.fn.DataTable.isDataTable(table)) table.DataTable().destroy();
                    table.html(html);
                    table.DataTable({
                        "language": LANGUAGES[locale],
                        //download table data options
                        dom: '<"dt-header">r<lf>tip<"dtf-butons"B>',
                        buttons: [
                            {
                                'extend': 'csv',
                                'className': 'btn btn-default',
                                'title': filename_export
                            },
                            {
                                'extend': 'excel',
                                'className': 'btn btn-default',
                                'title': filename_export
                            },
                            {   'extend': 'pdf',
                                'className': 'btn btn-default',
                                'title': filename_export
                            },
                        ],
                        "processing": true,
                    });

                    // Set title value
                    $("div.dt-header").html(title);
                } else {
                    this.el.text(this._('Table could not be created!'));
                }
            });
        },

        create_sql_string: function (main_value, y_axis, category_name, data_type) {

            // Get settings
            var sqlString = $('#sql-string').val() ? $('#sql-string').val() : this.options.sql_string;
            var parsedSqlString = sqlString.split('*');
            var sqlStringExceptSelect = parsedSqlString[1];

            // If category is set
            // we need the first column as a pivot column
            // see comments inside this.render_data_table_with_category
            // if data type is qualitative then only one column is needed
            if (data_type === 'qualitative') {
                return 'SELECT DISTINCT' + '"' + main_value + '"' + sqlStringExceptSelect + ' GROUP BY "' + main_value + '"';
            } else if (category_name) {
                return 'SELECT ' + '"' + category_name + '", "' + main_value + '", SUM("' + y_axis + '") as ' + '"' + y_axis + '"' + sqlStringExceptSelect + ' GROUP BY "' + category_name + '", "' + main_value + '"';
            } else {
                return 'SELECT ' + '"' + main_value + '", SUM("' + y_axis + '") as ' + '"' + y_axis + '"' + sqlStringExceptSelect + ' GROUP BY "' + main_value + '"';
            }

        },

        // default tables
        render_data_table: function (rows, main_value, y_axis) {
            main_value = typeof main_value === 'string' ? main_value.toLowerCase(): main_value;
            y_axis = typeof y_axis === 'string' ? y_axis.toLowerCase() : y_axis;

            // Prepare data
            var data = {
                main_value: main_value,
                y_axis: y_axis,
                dimension_label: this.capitalize(main_value),
                measure_label: this.capitalize(y_axis),
                rows: rows,
            }

            // Prepare template
            var template = `
          <table>
            <thead>
              <tr>
                <th>{dimension_label}</th>
                <th>{measure_label}</th>
              </tr>
            </thead>
            <tbody>
              {% for row in rows %}
                <tr>
                  <td>{row[main_value]}</td>
                  <td>{row[y_axis]|process_table_value}</td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
          `;

            //Render
            return this.render_template(template, data);
        },

        // table for the two-way columns feature
        render_data_table_with_category: function (rows, category_name, main_value, y_axis) {
            category_name = typeof category_name === 'string' ? category_name.toLowerCase() : category_name;
            main_value = typeof main_value === 'string' ? main_value.toLowerCase() : main_value;
            y_axis = typeof y_axis === 'string' ? y_axis.toLowerCase() : y_axis;

            // Prepare data
            // Pivot table when category is set
            // Source:
            //   category_name, main_value, y_axis
            //   cat1, string, number
            //   cat2, string, number
            // Target:
            //   main_value, y_axis for cat1, y_axis for cat2
            //   string, number, number
            //   string, number, number
            var rows_mapping = {};
            var y_axis_groups = {};
            for (let row of rows) {

                // Get ma
                if (!rows_mapping[row[main_value]]) rows_mapping[row[main_value]] = {};
                var mapping_item = rows_mapping[row[main_value]];

                // Pivot table
                mapping_item[main_value] = row[main_value];
                mapping_item[row[category_name]] = row[y_axis];

                // Sub headers
                y_axis_groups[row[category_name]] = true;
            };

            var data = {
                main_value: main_value,
                measure_label: this.capitalize(y_axis),
                y_axis: y_axis,
                dimension_label: this.capitalize(main_value),
                y_axis_groups: Object.keys(y_axis_groups).sort(),
                rows: Object.values(rows_mapping),
            };

            // Prepare template
            var template = `
          <table>
            <thead>
              <tr>
                <th rowspan="2">{dimension_label}</th>
                <th colspan="{y_axis_groups.length}">{measure_label}</th>
              </tr>
              <tr>
                {% for y_axis_group in y_axis_groups %}
                  <th>{y_axis_group}</th>
                {% endfor %}
              </tr>
            </thead>
            <tbody>
              {% for row in rows %}
                <tr>
                  <td>{row[main_value]}</td>
                  {% for y_axis_group in y_axis_groups %}
                    <td>{row[y_axis_group]|process_table_value}</td>
                  {% endfor %}
                </tr>
              {% endfor %}
            </tbody>
          </table>
          `;

            // Render
            return this.render_template(template, data);
        },

        // table for qualitative data with one column
        render_qualitative_data_table: function (rows, main_value) {
            main_value = main_value.toLowerCase();

            // Prepare data
            var data = {
                main_value: main_value,
                rows: rows,
            }

            // Prepare template
            var template = `
          <table>
            <thead>
              <tr>
                <th>{main_value|capitalize}</th>
              </tr>
            </thead>
            <tbody>
              {% for row in rows %}
                <tr>
                  <td>{row[main_value]}</td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
          `;

            //Render
            return this.render_template(template, data);
        },

        // render template unsing nunjucks
        render_template: function (template, data) {
            try {
                var env = nunjucks.configure({ tags: { variableStart: '{', variableEnd: '}' } });
                env.addFilter('process_table_value', this.process_table_value.bind(this))
                return env.renderString(template, data);
            } catch (error) {
                this.el.text(this._('Table could not be created!'));
                return '';
            }
        },

        //check for long decimal numbers and round to fixed 5 decimal points
        process_table_value: function (val) {
            if (isNaN(val)) return val;
            var dataf = (this.options.data_format === true) ? '' : this.options.data_format;
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
                val = Math.round(val * 10) / 10;
                format = d3.format(dataf);
                // Others
            } else {
                format = d3.format(dataf);
            }
            return format(val);
        },

        // count format decimals limited by "max"
        countDecimals: function (val, max) {
            return Math.min(val * 10 % 1 ? 2 : val % 1 ? 1 : 0, max);
        },

        updateTable: function () {
            var yVal = $('[name=table_field_y_axis_column]').val();
            var xVal = this.el.parent().parent().find('[id*=table_main_value]').val();
            var qualitativeData = this.el.parent().parent().find('[id*=table_data_type]');
            this.options.data_type = qualitativeData.is(':checked') ? 'qualitative' : 'quantitative';
            this.options.category_name = this.el.parent().parent().find('[id*=table_category_name]').val();
            this.options.data_format = this.el.parent().parent().find('[id*=table_data_format]').val();
            this.options.table_title = this.el.parent().parent().find('[id*=table_field_title]').val();

            this.createTable(yVal, xVal, true);
        },

        capitalize: function(s) {
            if (typeof s !== 'string') return s
            return s.charAt(0).toUpperCase() + s.slice(1)
        },

        teardown: function () {
            // We must always unsubscribe on teardown to prevent memory leaks.
            this.sandbox.unsubscribe('knowledgehub:updateTables', this.updateTable.bind(this));
        }
    }
});
