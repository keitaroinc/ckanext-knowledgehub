(function (_, jQuery) {
	'use strict';

    // Define all data source snippets
    var data_source_snippets = {
        'data_source_1': 'mssql_connection_params.html',
        'data_source_2': 'mssql_connection_params.html',
    }

	// Fetch CKAN snippet
	var api = {
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

	// Render CKAN snippet by passing data and errors values
	function renderSnippet(snippet, append_to, data, errors) {
		api.getTemplate(snippet, {
			data_source: data.data_source,
			server_name: data.server_name,
			db_username: data.db_username,
			db_password: data.db_password,
			query: data.query,
			data_source_error: errors.data_source,
			server_name_error: errors.server_name,
			db_username_error: errors.db_username,
			db_password_error: errors.db_password,
			query_error: errors.query
		})
		.done(function (data) {
			append_to.append(data);
		});
	}

	// Button for resetting the form when there is a data source select component
	function removeButton(data_source_select_div, connection_params_div, data_source_btn, image_upload_div) {
		var removeText = _('Remove');

		return $('<a href="javascript:;" class="btn btn-danger btn-remove-data-source pull-right">'
			+ removeText + '</a>')
			.prop('title', removeText)
			.on('click', {
				data_source_select_div: data_source_select_div,
				connection_params_div: connection_params_div,
				data_source_btn: data_source_btn,
				image_upload_div: image_upload_div
			}, onRemove)
	}

	// Handle on remove data source component
	function onRemove(e) {
		e.data.data_source_select_div.empty()
		e.data.connection_params_div.empty()
		e.data.data_source_btn.show();
		e.data.image_upload_div.show();
		$(this).hide();
	}

	$(document).ready(function () {
		var data_source_div = $('div.data-source');
		var data_source_btn = $('button.btn-data-source');
		var image_upload_div = $('div.image-upload');
		var data_source_select_div = $('div.data-source div.select-form');
		var connection_params_div = $('div.data-source div.connection-params');
		var field_image_url_input = $('input#field-image-url');
        var field_image_upload_input = $('input#field-image-upload');
        var field_name_input = $('input#field-name');

		try {
			var data = JSON.parse(
				$('input#form-data').val()
					.replace(/u/g, '')
					.replace(/'/g, '"')
					.replace(/None/g, '""')
					.replace(/True/g, 'true')
					.replace(/False/g, 'false')
			);
		} catch (error) {
			data = ''
			if (console) {
				console.error('Error parsing input#form-data: ' + error);
			}
		}

		try {
			var errors = JSON.parse(
				$('input#form-errors').val()
					.replace(/u/g, '')
					.replace(/'/g, '"')
					.replace(/None/g, '""')
					.replace(/True/g, 'true')
					.replace(/False/g, 'false')
			);
		} catch (error) {
			error = ''
			if (console) {
				console.error('Error parsing input#form-errors: ' + error);
			}
		}

		// If there is already selected resource, hide data source button
		if (field_image_url_input.val() !== '' || field_image_upload_input.val() !== '') {
			data_source_btn.hide();
		}

		// If there is already selected data source, show it with populated fields
		if (data.data_source) {
			var remove_button = removeButton(data_source_select_div,
 											 connection_params_div,
											 data_source_btn,
											 image_upload_div)

			image_upload_div.hide();
			data_source_btn.hide();
			data_source_div.prepend(remove_button);

			renderSnippet(
				'select_source.html',
				data_source_select_div,
				data,
				errors
			);

			renderSnippet(
				data_source_snippets[data.data_source],
				data_source_select_div,
				data,
				errors
			);
		}

		// If file is chosen from file field-nameystem then hide the data source button
		field_image_upload_input.change(function () {
			data_source_btn.hide();
		});

		// If remove button is clicked show data source button.
		// If link button is clicked hide data source button
		image_upload_div.click(function (e) {
			if (e.target.innerText === 'Link') {
				data_source_btn.hide();
			}

			if (e.target.innerText === 'Remove') {
                data_source_btn.show();
                field_name_input.val('');
			}
		});

		// Handle click on data source button
		data_source_btn.click(function (e) {
			var remove_button = removeButton(data_source_select_div,
											 connection_params_div,
											 data_source_btn,
											 image_upload_div)

			image_upload_div.hide();
			data_source_btn.hide();
			data_source_div.prepend(remove_button);

			renderSnippet(
				'select_source.html',
				data_source_select_div,
				data,
				errors
			);
		});

		// Render snippet for db connection params and query when data source is chosen
		$('body').on('change', '.select-source', function () {
			if (this.value !== '') {
				connection_params_div.empty();

				renderSnippet(
					data_source_snippets[this.value],
					connection_params_div,
					data,
					errors
				);
			}
		});
	});

})(ckan.i18n.ngettext, $);