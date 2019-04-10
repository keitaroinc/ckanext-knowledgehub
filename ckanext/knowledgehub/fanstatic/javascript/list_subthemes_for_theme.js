(function (_, jQuery) {
    'use strict';

    var api = {
        get: function (action, params, async) {
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
        }
    };

    function populateSubThemes() {
        var theme = $('#field-theme').val();
        var selected = $('#field-sub_theme').val();

        api.get('sub_theme_list', {
            'theme': theme
        }, true)
        .done(function (data) {
            document.getElementById("field-sub_theme").options.length = 0;                

            if(data.result.data.length != 0)
            {
                $('#field-sub_theme').append(new Option("Select sub-theme"), '');
                if(theme !="")
                    for (var i = 0; i < data.result.data.length; ++i) {
                        $('#field-sub_theme').append(new Option(data.result.data[i].title, data.result.data[i].id));
                        if(data.result.data[i].id == selected) {
                            // select new index and trigger change for visual change
                            $('#field-sub_theme').get(0).selectedIndex = i + 1;
                            $('#field-sub_theme').trigger('change');

                        }
                    }
                else
                {
                    $('#field-sub_theme').empty();
                    $('#field-sub_theme').append(new Option("Please select a theme first!"));  
                } 
            }
            else {
                $('#field-sub_theme').append(new Option("This theme does not have any sub-themes"));
            }
        });
    }

    function populateRQ() {
        var theme = $('#field-theme').val();
        var sub_theme = $('#field-sub_theme').val();
        var rq_list = $('#field-research_question').val(); // this is where we get the empty list
        console.log(theme);
        console.log(sub_theme);
        console.log(rq_list);
        api.get('research_question_list', {
            'theme': theme,
            'sub_theme': sub_theme
        }, true)
        .done(function (data) {
            var rq = document.getElementById("field-research_question");
            if(rq) {
                $('#research_question').empty();
                rq.options.length = 0;
                for (var i = 0; i < data.result.data.length; ++i) {
                    rq.options[rq.options.length] = new Option(data.result.data[i].title);
                }
            }
        });
    }

    $(window).on("load", function() {
        // we need to populate sub themes on load, since we need the data from the html
        populateSubThemes();
});
    $(document).ready(function () {
        
        $('#field-theme').change(function () {
            document.getElementById("field-research_question").options.length = 0;
            $('.select2-container').select2('val', '');
            populateSubThemes();
            
        });

        $('#field-sub_theme').change(function () {
            populateRQ();
        });
    });
})(ckan.i18n.ngettext, $);

