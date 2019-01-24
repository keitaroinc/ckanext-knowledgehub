(function (_, jQuery) {
	'use strict';

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

	function onRemove(e) {
		e.data.data_source_select_div.empty()
		e.data.connection_params_div.empty()
		e.data.data_source_btn.show();
		e.data.image_upload_div.show();
		$(this).hide();
	}

	$(document).ready(function () {
		var data_source_div = $('div.data-source')
		var data_source_btn = $('button.btn-data-source')
		var image_upload_div = $('div.image-upload')
		var data_source_select_div = $('div.data-source div.select-form')
		var connection_params_div = $('div.data-source div.connection-params')

		$('div.image-upload div.form-group div.controls').click(function (e) {
			if (e.target.innerText == 'Link') {
				data_source_btn.hide()
			}

			if (e.target.innerText == 'Remove') {
				data_source_btn.show()
			}
		});

		data_source_btn.click(function (e) {
			// Button for resetting the form when there is a data source select component
			var removeText = _('Remove');
			var remove_button = $('<a href="javascript:;" class="btn btn-danger btn-remove-data-source pull-right">'
								+ removeText + '</a>')
								.prop('title', removeText)
								.on('click', {
									data_source_select_div: data_source_select_div,
									connection_params_div: connection_params_div,
									data_source_btn: data_source_btn,
									image_upload_div: image_upload_div
								}, onRemove)

			image_upload_div.hide();
			data_source_btn.hide();
			data_source_div.prepend(remove_button);

			api.getTemplate('select_source.html', {
				data: {},
				errors: {}
			})
			.done(function (data) {
				data_source_select_div.append(data);
			})
		});

		$('body').on('change', '.select-source', function () {
			if (this.value != '') {
				connection_params_div.empty()
				api.getTemplate('mssql_connection_params.html', {
					data: {},
					errors: {}
				})
				.done(function (data) {
					connection_params_div.append(data);
				})
			}
		});
	});


})(ckan.i18n.ngettext, $);