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

	$(document).ready(function () {
		var data_source_elements = $('.data-source')
		var data_source_btn = $('.btn-data-source')

		$('div.image-upload div.form-group div.controls').click(function (e) {
			if (e.target.innerText == 'Link') {
					data_source_btn.hide()
			}

			if (e.target.innerText == 'Remove') {
					data_source_btn.show()
			}
		});

		data_source_btn.click(function (e) {
			api.getTemplate('select_source.html', {
				data: {},
				errors: {}
			})
			.done(function (data) {
				data_source_elements.prepend(data);
			})
		});

		$('body').on('change', '.select-sources', function () {
			console.log(this.value)
			api.getTemplate('select_source.html', {
				data: {},
				errors: {}
			})
			.done(function (data) {
				data_source_elements.prepend(data);
			})
		});
	});


})(ckan.i18n.ngettext, $);